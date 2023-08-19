#!/usr/bin/env python3
# -*- coding: utf-8 -*- ®

from sqlalchemy import Column, Integer, String, DateTime, Index
from sqlalchemy import literal_column
from db.helper import get_base
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql import func

Base = get_base()


class Block(Base):
    __tablename__ = 'block'
    id = Column(Integer, primary_key=True)
    inetnum = Column(postgresql.CIDR, nullable=False, index=True)
    netname = Column(String, nullable=True, index=True)
    description = Column(String)
    country = Column(String, index=True)
    maintained_by = Column(String, index=True)
    created = Column(DateTime, index=True)
    last_modified = Column(DateTime, index=True)
    source = Column(String, index=True)
    status = Column(String, index=True)

    __table_args__ = (
        Index('ix_block_description', func.to_tsvector(literal_column("'english'"), description), postgresql_using="gin"), )

    def __str__(self):
        return f'inetnum: {self.inetnum}, netname: {self.netname}, desc: {self.description}, status: {self.status}, country: {self.country}, maintained: {self.maintained_by}, created: {self.created}, updated: {self.last_modified}, source: {self.source}'

    def __repr__(self):
        return self.__str__()
