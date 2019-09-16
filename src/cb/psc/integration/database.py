import enum
import logging
from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    create_engine,
    orm
)
from sqlalchemy.exc import DatabaseError
from sqlalchemy.ext.declarative import as_declarative
from sqlalchemy.orm import scoped_session, sessionmaker

from cb.psc.integration.config import config

log = logging.getLogger(__name__)
log.setLevel(config.loglevel)

engine = create_engine(config.database_url)
session = scoped_session(sessionmaker(bind=engine))


def init_db():
    log.debug("init_db called")
    Base.metadata.create_all(engine)


@as_declarative()
class Base(object):
    id = Column(Integer, primary_key=True)

    query = session.query_property()

    @classmethod
    def create(cls, **kwargs):
        m = cls(**kwargs)
        return m.save()

    def save(self):
        session.add(self)
        try:
            session.commit()
        except DatabaseError:
            session.rollback()
            raise
        return self

    def update(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)
        return self.save()

    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class Binary(Base):
    """
    Represents a binary that has been (or will be) visited by the connectors.
    """

    __tablename__ = "binaries"

    sha256 = Column(String(64), unique=True, nullable=False)
    """
    The SHA256 hash of the binary.
    """

    available = Column(Boolean, default=False)
    """
    Whether or not the binary is currently available in the cache.
    """

    @classmethod
    def from_hash(cls, hash):
        """
        Returns the binary associated with the given hash if available in the
        cache, or None if unavailable.
        """
        return cls.query.filter(cls.sha256 == hash).one_or_none()

    @property
    def data_key(self):
        return f"/binaries/{self.sha256}"

    @property
    def count_key(self):
        return f"{self.data_key}/refcount"


class IOC(Base):
    """
    Models an indicator of compromise detected during an analysis.

    Every IOC belongs to an AnalysisResult.
    """

    __tablename__ = "iocs"

    class MatchType(str, enum.Enum):
        """
        Represents the valid matching strategies for an IOC.
        """

        Equality: str = "equality"
        Regex: str = "regex"
        Query: str = "query"

    analysis_id = Column(
        Integer, ForeignKey("analysis.id", deferrable=True, initially="DEFERRED"), nullable=False
    )
    match_type = Column(Enum(MatchType), nullable=False)
    values = Column(JSON, nullable=False)
    field = Column(String, nullable=True)
    link = Column(String, nullable=True)

    def as_dict(self):
        return {
            "id": str(self.id),
            "match_type": self.match_type,
            "values": list(self.values),
            "field": self.field,
            "link": self.link,
        }


class AnalysisResult(Base):
    """
    Models the result of an analysis performed by a connector.

    Use :py:meth:`Connector.result` to create these models.
    """

    __tablename__ = "analysis"

    sha256 = Column(String(64), nullable=False)
    """
    The SHA256 hash of the analyzed binary.

    :rtype: str
    """

    connector_name = Column(String(64), nullable=False)
    """
    The name of the connector that this analysis originated from.

    :rtype: str
    """

    analysis_name = Column(String(64), nullable=False)
    """
    The name of the analysis pass.

    :rtype: str
    """

    score = Column(Integer, default=0)
    """
    The score assigned to this binary by the analysis pass.

    Default: 0

    :rtype: int
    """

    error = Column(Boolean, default=False)
    """
    Whether the analysis failed.

    Default: False

    :rtype: bool
    """

    scan_time = Column(DateTime, default=datetime.utcnow, nullable=False)
    """
    When the analysis was performed.

    Default: :py:meth:`datetime.utcnow`

    :rtype: :py:class:`DateTime`
    """

    iocs = orm.relationship("IOC", backref="analysis", cascade="all, delete-orphan", lazy=False)
    """
    Any IOCs produced by this analysis.

    :rtype: list
    """

    job_id = Column(String(36), nullable=False)
    """
    The ID of the job that ran the analysis.

    :rtype: str
    """

    dispatched = Column(Boolean, default=False)
    """
    Whether this result has been dispatched to a feed.

    :rtype: bool
    """

    @property
    def binary(self):
        """
        Returns the :py:class:`database.Binary` associated with this result.

        :rtype: :py:class:`database.Binary`

        Example::

        >>> result.binary.sha256 == result.sha256
        """
        # TODO(ww): This could probably be a relation instead.
        return Binary.from_hash(self.sha256)

    def ioc(self, *, match_type=IOC.MatchType.Equality, values, field=None, link=None):
        """
        Attaches a new IOC to this result.

        :param match_type: The matching strategy for this IOC
        :type match_type: :py:class:`database.IOC.MatchType`
        :param values: The list of values for this IOC
        :type values: list
        :param field: The corresponding process field
        :type field: str or None
        :param link: A link to a description of the IOC
        :type link: str or None
        :rtype: :py:class:`database.IOC`

        """
        return IOC.create(
            analysis=self, match_type=match_type, values=values, field=field, link=link
        )

    def normalize(self):
        """
        Normalizes this result to make it palatable for the CbTH backend.
        """
        if self.score <= 0 or self.score > 10:
            log.warning(f"normalizing OOB score: {self.score}")
            self.update(score=max(1, int(self.score/10)))
            #self.update(score=max(1, min(self.score, 10)))
            # NOTE: min 1 and ot 0 
                # else err 400 from cbapi: Report severity must be between 1 and 10
        return self

    def __str__(self):
        return f"{self.connector_name}:{self.analysis_name}:{self.sha256}"
