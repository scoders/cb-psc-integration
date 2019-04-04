from cb.psc.integration import database


def main():
    # TODO(ww): Config.
    database.Base.metadata.create_all(database.engine)


if __name__ == '__main__':
    main()
