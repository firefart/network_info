#!/usr/bin/env python3
# -*- coding: utf-8 -*- ®

from sqlalchemy import Column, ForeignKey, Integer, String, DateTime
from sqlalchemy.orm import relationship
from db.helper import get_base
from sqlalchemy.dialects import postgresql

Base = get_base()


class Block(Base):
    __tablename__ = 'block'
    id = Column(Integer, primary_key=True)
    inetnum = Column(postgresql.CIDR, nullable=False, index=True)
    netname = Column(String, nullable=True, index=True)
    description = Column(String, index=True)
    country = Column(String, index=True)
    maintained_by = Column(String, index=True)
    created = Column(DateTime, index=True)
    last_modified = Column(DateTime, index=True)
    source = Column(String, index=True)

    def __str__(self):
        return 'inetnum: {}, netname: {}, desc: {}, country: {}, maintained: {}, created: {}, updated: {}, source: {}'.format(
            self.inetnum, self.netname, self.description, self.country,
            self.maintained_by, self.created, self.last_modified, self.source)

    def __repr__(self):
        return self.__str__()
