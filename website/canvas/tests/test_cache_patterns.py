from canvas.cache_patterns import CachedCall, DoesNotExist, InProcessCache, memoize, invalidates_cache, cache
from canvas.models import Comment
from canvas.tests.tests_helpers import CB, create_comment, create_content, CanvasTestCase


class NoCache(object):
    def get(self, key):
        return DoesNotExist
        
    def set(self, key, value):
        pass
        
    def flush(self):
        pass
        
    def __contains__(self, other):
        return False


class TestCacheDecorators(CanvasTestCase):
    def after_setUp(self):
        cache.flush_all()

    def test_invalidates_cache_with_cached_call(self):
        TIMEOUT = 22
        key = "cache_key"
        
        @memoize(key=key, time=TIMEOUT)
        def memoized():
            return "ok"
        
        # memoized() returns an instance of CachedCall.
        @invalidates_cache(memoized)
        def invalidates():
            pass
        
        cc = memoized()
        # Execute the CachedCall to set the cache
        cc()
        self.assertEqual('"ok"', cache.get(key))
        invalidates()
        self.assertEqual(None, cache.get(key))
        self.assertEqual(DoesNotExist, CachedCall.inprocess_cache.get(key))
        
    def test_memoize(self):
        TIMEOUT = 22
        key = "cache_key"
        @memoize(key=key, time=TIMEOUT)
        def memoized(foo):
            return "ok"
        
        cc = memoized(123)
        self.assertTrue(isinstance(cc, CachedCall))
        self.assertEqual("ok", cc())
        
        self.assertEqual(TIMEOUT, cc.timeout)
        self.assertEqual(cc.key, key)
        
        
class TestCachedCallWithoutInProcessCache(CanvasTestCase):
    def after_setUp(self):
        CachedCall.inprocess_cache = NoCache()
        cache.flush_all()
        
    def before_tearDown(self):
        CachedCall.inprocess_cache = InProcessCache()
        
    def test_first_call_returns_value(self):
        fun = CB()
        cc = CachedCall('key', fun)
        
        self.assertEquals(fun.retvalue, cc())
        self.assertEquals(1, fun.called)
    
    def test_second_call_returns_value_without_calling_underlying_function(self):
        fun = CB()
        cc = CachedCall('key', fun)
        cc()

        self.assertEquals(fun.retvalue, cc())
        self.assertEquals(1, fun.called)
        
    def test_cache_stores_json_correctly(self):
        fun = CB(retvalue={'foo': ['bar']})
        cc = CachedCall('key', fun)
        
        self.assertEquals(fun.retvalue, cc())
        self.assertEquals(fun.retvalue, cc())
        self.assertEquals(1, fun.called)
        
    def test_two_cachedcalls_with_different_keys_dont_interfere(self):
        f1 = CB(retvalue=1)
        f2 = CB(retvalue=2)
        
    def test_force_returns_new_value(self):
        fun = CB(retvalue=1)
        cc = CachedCall('key', fun)
        cc()
        
        fun.retvalue = 2
        self.assertEqual(2, cc.force())

    def test_force_updates_cached_value(self):
        fun = CB(retvalue=1)
        cc = CachedCall('key', fun)
        cc()

        fun.retvalue = 2
        cc.force()
        self.assertEqual(2, cc())
        
    def test_two_cachedcalls_with_same_key_use_same_cache(self):
        fun = CB(retvalue='bar')
        cc1 = CachedCall('qix', fun)
        cc2 = CachedCall('qix', fun)
        
        self.assertEqual(cc1(), cc2())
        self.assertEqual(1, fun.called)
        
    def test_decorator(self):
        tocache = {'animals': 2}
        toadd = {'people': 3}
        decorator = lambda c: dict(c, **toadd)
        expected = dict(tocache, **toadd)
        
        fun = CB(retvalue=tocache)
        cc = CachedCall('key', fun, decorator=decorator)
        self.assertEquals(expected, cc())
        # Now test cached.
        cc = CachedCall('key', fun, decorator=decorator)
        self.assertEquals(expected, cc())
        self.assertEquals(1, fun.called)
        
    def test_skip_decorator(self):
        def decorator(self):
            raise Exception
            
        fun = CB()
        cc = CachedCall('key', fun, decorator=decorator)
        self.assertEquals(fun.retvalue, cc(skip_decorator=True))
        self.assertEquals(fun.retvalue, cc.force(skip_decorator=True))
        
    def test_uncached_call_returns_jsonlike_result(self):
        fun = CB(retvalue={1: 'bar'})
        cc = CachedCall('key', fun)
        
        self.assertEquals({'1': 'bar'}, cc())
        self.assertEquals({'1': 'bar'}, cc.force())
        
    def test_empty_multicall_returns_empty_results(self):
        self.assertEquals([], CachedCall.multicall([]))
        
    def test_multicall_returns_correct_results(self):
        funs = [CB(retvalue=n) for n in [1,2,3,4,5]]
        calls = [CachedCall("key_%s" % e, fun) for e,fun in enumerate(funs)]
        
        # Uncached
        self.assertEquals([1,2,3,4,5], CachedCall.multicall(calls))
        
        # Cached
        self.assertEquals([1,2,3,4,5], CachedCall.multicall(calls))
        self.assertEquals([1] * len(funs), [fun.called for fun in funs])

    def test_multicall_half_cached_returns_results(self):
        funs = [CB(retvalue=n) for n in [1,2,3,4,5]]
        calls = [CachedCall("key_%s" % e, fun) for e,fun in enumerate(funs)]

        # Uncached
        self.assertEquals([1,2,3], CachedCall.multicall(calls[:3]))
        
        # Half cached
        self.assertEquals([1,2,3,4,5], CachedCall.multicall(calls))
        self.assertEquals([1] * len(funs), [fun.called for fun in funs])
        
    def test_many_multicall(self):
        f1, f2, f3, f4, f5, f6 = [CachedCall('key_%s' % n, CB(retvalue=n)) for n in [1,2,3,4,5,6]]
        
        self.assertEquals([[1], [2,3], [4,5,6]], CachedCall.many_multicall([f1], [f2, f3], [f4, f5, f6]))


class TestQuerysetCacheShortcut(CanvasTestCase):
    def test_queryset_details(self):
        comments = [create_comment(reply_content=create_content()) for _ in xrange(10)]
        details1 = CachedCall.multicall([cmt.details for cmt in comments])

        queryset = Comment.objects.filter(id__in=[cmt.id for cmt in comments])
        details2 = CachedCall.queryset_details(queryset)

        self.assertEquals(details1, details2)


class TestInprocessCacheClassVariable(CanvasTestCase):
    def test_inprocess_cache_persists(self):
        def calc():
            return 42
        
        def func():
            return CachedCall("key", calc)
        
        cc1 = func()
        cc2 = func()
        
        self.assertEqual(42, cc1())
        self.assertEqual(42, cc2())
        print cc1.inprocess_cache
        print cc2.inprocess_cache
        # Make sure that inprocess_cache is a class variable.
        self.assertEqual(cc1.inprocess_cache, cc2.inprocess_cache)
        

class TestInProcessCache(CanvasTestCase):
    def after_setUp(self):
        cache.flush_all()
        CachedCall.inprocess_cache = InProcessCache()
    
    def test_inprocess_cache_prevents_multiple_calls_multiple_fetch(self):
        fun = CB()
        cc = CachedCall('key', fun)
        self.assertEqual(fun.retvalue, cc())
        cache.delete('key')
        
        self.assertEqual(fun.retvalue, cc())
        self.assertEqual(1, fun.called)
        
        
    def test_inprocess_cached_prevents_multiple_fetches_in_multicall(self):
        funs = [CB(retvalue=n) for n in [1,2,3,4,5]]
        calls = [CachedCall("key_%s" % e, fun) for e,fun in enumerate(funs)]

        # Uncached
        self.assertEquals([1,2,3], CachedCall.multicall(calls[:3]))
        
        # Remove some of the backing stores
        cache.delete('key_0')
        cache.delete('key_1')
        CachedCall.inprocess_cache.delete('key_2')
        
        
        # 1,2 in-process only, 3 in redis only, 4,5 uncached
        self.assertEquals([1,2,3,4,5], CachedCall.multicall(calls))
        self.assertEquals([1] * len(funs), [fun.called for fun in funs])

        
