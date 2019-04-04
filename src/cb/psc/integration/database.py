from .config import config

from sqlalchemy import Column, Integer, String, DateTime, Boolean, create_engine
from sqlalchemy.ext.declarative import as_declarative
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.schema import UniqueConstraint
from sqlalchemy.exc import DatabaseError

from datetime import datetime
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

engine = create_engine(config.database)
session = scoped_session(sessionmaker(bind=engine))


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
    __tablename__ = "binaries"

    sha256 = Column(String(64), unique=True, nullable=False)
    available = Column(Boolean, default=False)

    @classmethod
    def from_hash(cls, hash):
        return cls.query.filter(cls.sha256 == hash).one_or_none()


class AnalysisResult(Base):
    """
    Models the result of an analysis performed by a connector.
    """

    __tablename__ = "results"
    __table_args__ = (
        UniqueConstraint(
            "sha256", "connector_name", "analysis_name", name="_result_uc"
        ),
    )

    # The hash of the analyzed binary.
    sha256 = Column(String(64), nullable=False)

    # The name of the connector that this analysis originated from.
    connector_name = Column(String(64), nullable=False)

    # The name of the analysis pass.
    analysis_name = Column(String(64), nullable=False)

    # The score assigned to this binary by the analysis pass.
    score = Column(Integer, default=0)

    # Whether the analysis failed.
    error = Column(Boolean, default=False)

    # When the analysis was performed.
    scan_time = Column(DateTime, default=datetime.utcnow, nullable=False)

    @property
    def binary(self):
        return Binary.from_hash(self.sha256)
