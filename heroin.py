
import inspect
import types
from copy import copy

class InjectionException(Exception):
  def __init__(self, message):
    Exception.__init__(self, message)


class Injector(object):
  def __init__(self, seed_values, *providers, **kwargs):
    self.seed_values = seed_values
    self.providers = {}
    self.parent = kwargs.get('parent')
    self.deps = copy(seed_values)

    for p in providers:
      if type(p) == dict:
        for name, func in p.iteritems():
          self.providers[name] = func
      else:
        # Assume is class or class instance
        for member_name, t in inspect.getmembers(p):
          member = getattr(p, member_name)
          if hasattr(member, 'provides'):
            print "MEMBER", member
            self.providers[member.provides['name']] = member

  def child(self, seed_values, *providers):
    """create a child scope"""
    return Injector(seed_values, parent=self, *providers)

  def invoke(self, funclike, *vargs, **extras):
    """invokes the given function, constructor, or callable,
    sourcing arguments from the scope.

    args may be explicitly overridden by using keyword args,
    unused keword args will be passed through as keyword args.

    var args will be passed through as var args only."""

    arg_source = funclike
    while hasattr(arg_source, '__call__') and \
        type(arg_source.__call__) != wrapper_type:
      arg_source = arg_source.__call__

    args, kwargs = self.resolve_args(arg_source, **extras)

    return funclike(*(args + vargs), **kwargs)

  def resolve(self, name):
    if self.deps.has_key(name):
      return self.deps[name]

    provider = self.providers.get(name)
    if provider:
      dep = self.invoke(provider)
      self.deps[name] = dep
      return dep

    if self.parent:
      return self.parent.resolve(name)

    raise InjectionException('Could not resolve %s' % name)

  def resolve_args(self, func, **explicit_args):
    # consider ignoring args with default values, if
    # values not available in scope. (use the .defaults
    # property)

    while hasattr(func, '__call__') and type(func.__call__) != wrapper_type:
      func = func.__call__

    argnames = inspect.getargspec(func).args

    if self._is_bound_method(func):
      # skip the self arg, which is already applied.
      # kinda odd that the bound wrapper doesn't expose only
      # the modified argument list.
      # Apparently in python 3.0 this is no longer an issue.
      argnames = argnames[1:]

    args = []

    for name in argnames:
      if explicit_args.has_key(name):
        args.append(explicit_args.pop(name))
      else:
        args.append(self.resolve(name))

    return (tuple(args), explicit_args) # return args, and unused explicit args.

  def _is_bound_method(self, method):
    t = type(method)
    return t == type(self.__init__)


def dummy(): pass
wrapper_type = type(dummy.__call__)

def provider_inner(name, func, **kwargs):
  info = kwargs
  info['name'] = name
  func.provides = info
  return func

def provides(arg, **kwargs):
  if type(arg) == str:
    name = arg
    return lambda(func): provider_inner(name, func, **kwargs)
  else:
    func = arg
    return provider_inner(func.func_name, func, **kwargs)


### examples


class MyProviders(object):

  @provides('foo')
  def blah(self, x):
    print x

  @staticmethod
  @provides
  def thisworkstoo(x):
    return 'lkajsdf'



main_scope = Injector({'a':5}, {'foo':lambda a: a + 6}, MyProviders())

# Can make child scopes, e.g.
# request_scope = main_scope.child({'request':request}, RequestProviders)




