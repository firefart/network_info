#!/usr/bin/env python3
# -*- coding: utf-8 -*- ®

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

Base = declarative_base()


def get_base():
    return Base


def setup_connection(create_db=False):
    engine = create_postgres_pool()
    session = sessionmaker()
    session.configure(bind=engine)

    if create_db:
        Base.metadata.drop_all(engine)
        Base.metadata.create_all(engine)

    return session()


def create_postgres_pool():
    engine = create_engine('postgresql://ripe:ripe@localhost/ripe')
    return engine
