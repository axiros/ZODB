##############################################################################
#
# Copyright (c) 2001, 2002 Zope Foundation and Contributors.
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
"""Test the routines to convert between long and 64-bit strings"""
import doctest
import random
import re
import unittest
from persistent import Persistent

from zope.testing import renormalizing
from ZODB.utils import U64, p64, u64
from ZODB._compat import loads, long


NUM = 100


checker = renormalizing.RENormalizing([
    # Python 3 bytes add a "b".
    (re.compile("b('.*?')"),
     r"\1"),
    ])

class TestUtils(unittest.TestCase):

    small = [random.randrange(1, 1<<32, int=long)
             for i in range(NUM)]
    large = [random.randrange(1<<32, 1<<64, int=long)
             for i in range(NUM)]
    all = small + large

    def checkLongToStringToLong(self):
        for num in self.all:
            s = p64(num)
            n = U64(s)
            self.assertEqual(num, n, "U64() failed")
            n2 = u64(s)
            self.assertEqual(num, n2, "u64() failed")

    def checkKnownConstants(self):
        self.assertEqual(b"\000\000\000\000\000\000\000\001", p64(1))
        self.assertEqual(b"\000\000\000\001\000\000\000\000", p64(1<<32))
        self.assertEqual(u64(b"\000\000\000\000\000\000\000\001"), 1)
        self.assertEqual(U64(b"\000\000\000\000\000\000\000\001"), 1)
        self.assertEqual(u64(b"\000\000\000\001\000\000\000\000"), 1<<32)
        self.assertEqual(U64(b"\000\000\000\001\000\000\000\000"), 1<<32)

    def checkPersistentIdHandlesDescriptor(self):
        from ZODB.serialize import ObjectWriter
        class P(Persistent):
            pass

        writer = ObjectWriter(None)
        self.assertEqual(writer.persistent_id(P), None)

    # It's hard to know where to put this test.  We're checking that the
    # ConflictError constructor uses utils.py's get_pickle_metadata() to
    # deduce the class path from a pickle, instead of actually loading
    # the pickle (and so also trying to import application module and
    # class objects, which isn't a good idea on a ZEO server when avoidable).
    def checkConflictErrorDoesntImport(self):
        from ZODB.serialize import ObjectWriter
        from ZODB.POSException import ConflictError
        from ZODB.tests.MinPO import MinPO

        obj = MinPO()
        data = ObjectWriter().serialize(obj)

        # The pickle contains a GLOBAL ('c') opcode resolving to MinPO's
        # module and class.
        self.assertTrue(b'cZODB.tests.MinPO\nMinPO\n' in data)

        # Fiddle the pickle so it points to something "impossible" instead.
        data = data.replace(b'cZODB.tests.MinPO\nMinPO\n',
                            b'cpath.that.does.not.exist\nlikewise.the.class\n')
        # Pickle can't resolve that GLOBAL opcode -- gets ImportError.
        self.assertRaises(ImportError, loads, data)

        # Verify that building ConflictError doesn't get ImportError.
        try:
            raise ConflictError(object=obj, data=data)
        except ConflictError as detail:
            # And verify that the msg names the impossible path.
            self.assertTrue(
                'path.that.does.not.exist.likewise.the.class' in str(detail))
        else:
            self.fail("expected ConflictError, but no exception raised")


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestUtils, 'check'))
    suite.addTest(doctest.DocFileSuite('../utils.txt', checker=checker))
    return suite
