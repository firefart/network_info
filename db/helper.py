#!/usr/bin/env python3
# -*- coding: utf-8 -*- ®

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

Base = declarative_base()


def get_base():
    return Base


def setup_connection(connection_string, create_db=False):
    engine = create_postgres_pool(connection_string)
    session = sessionmaker()
    session.configure(bind=engine)

    if create_db:
        Base.metadata.drop_all(engine)
        Base.metadata.create_all(engine)

    return session()


def create_postgres_pool(connection_string):
    engine = create_engine(connection_string)
    return engine
