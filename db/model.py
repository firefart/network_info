#!/usr/bin/env python
# -*- coding: utf-8 -*- ®

from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from db.helper import get_base
from sqlalchemy.dialects import postgresql

Base = get_base()


class Block(Base):
    __tablename__ = 'block'
    id = Column(Integer, primary_key=True)
    inetnum = Column(String, nullable=False)
    netname = Column(String, nullable=False, index=True)
    description = Column(String, index=True)
    country = Column(String, index=True)
    maintained_by = Column(String, index=True)

    def __str__(self):
        return 'inetnum: {}, netname: {}, desc: {}, country: {}, maintained: {}'.format(self.inetnum, self.netname,
                                                                                        self.description, self.country,
                                                                                        self.maintained_by)

    def __repr__(self):
        return self.__str__()


class Cidr(Base):
    __tablename__ = 'cidr'
    id = Column(Integer, primary_key=True)
    cidr = Column(postgresql.CIDR, nullable=False, index=True)
    block_id = Column(Integer, ForeignKey('block.id'))
    block = relationship(Block)

    def __str__(self):
        return 'cidr: {}, blockid: {}'.format(self.cidr, self.block_id)

    def __repr__(self):
        return self.__str__()
