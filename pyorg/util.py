"""Misc. utility code."""

from abc import ABC
from collections import ChainMap
import re
from datetime import date, datetime, timedelta, timezone


class SingleDispatchMethod:
	"""Version of a :class:`.SingleDispatchBase` which acts as a method.

	Attributes
	----------
	func : .SingleDispatchBase
	instance
		Instance the function is bound to, or None.
	owner
	"""

	def __init__(self, func, instance, owner=None):
		self.func = func
		self.instance = instance
		self.owner = owner
		self.__doc__ = func.__doc__

	def dispatch(self, arg):
		impl = self.func.dispatch(arg)
		return impl.__get__(self.instance, self.owner)

	def __call__(self, arg, *rest, **kwargs):
		impl = self.dispatch(arg)
		return impl(arg, *rest, **kwargs)

	@property
	def default(self):
		return self.func.default.__get__(self.instance, self.owner)


class SingleDispatchBase(ABC):
	"""ABC for a generic function which dispatches on some trait of its first argument.

	May be bound to an object or class as a method.

	Concrete subclasses must implement one of the :meth:`get_key` or
	:meth:`iter_keys()` method.

	Attributes
	----------
	default : callable
		Default implementation.
	registry : dict
		Stores the specialized implementation functions by key.
	"""

	def __init__(self, default, registry=None, doc=None):
		self.default = default
		self.registry = {} if registry is None else registry
		self.__doc__ = doc if doc is not None else default.__doc__

	def bind(self, instance, owner=None):
		"""Get a version of the function bound to the given instance as a method.

		Parameters
		----------
		instance
			Object instance to bind to.
		owner
		"""
		return self if instance is None else SingleDispatchMethod(self, instance, owner)

	def __get__(self, instance, owner):
		return self.bind(instance, owner)

	def get_key(self, arg):
		"""Get the key to look up the correct implementation for the given argument."""
		raise NotImplementedError()

	def iter_keys(self, arg):
		yield self.get_key(arg)

	def dispatch(self, arg):
		"""Get the actual function implementation for the given argument.
		"""
		for key in self.iter_keys(arg):
			try:
				return self.registry[key]
			except KeyError:
				pass

		return self.default

	def validate_key(self, key):
		"""
		Validate and possibly replace a key before an implementation is
		registered under it.

		Default implementation simply returns the argument. Subclasses may wish
		to override this. An error should be raised for invalid keys.

		Parameters
		----------
		key
			Key passed to :meth:`register`.

		Returns
		-------
			Key to use for registration, which may be different than argument.
		"""
		return key

	def register(self, key, impl=None):
		"""Register an implementation for the given key.

		Parameters
		----------
		key
			Key to register method under. May also be a list of keys.
		impl : callable
			Implementation to register under the given key(s). If None will
			return a decorator function that completes the registration.

		Returns
		-------
		function or None
			None if ``method`` is given. Otherwise returns a decorator that will
			register the function it is applied to.
		"""
		if isinstance(key, list):
			keys = list(map(self.validate_key, key))
		else:
			keys = [self.validate_key(key)]

		def decorator(impl):
			if not callable(impl):
				raise TypeError('Implementation must be a callable object')

			for key in keys:
				self.registry[key] = impl

			return impl

		if impl is None:
			return decorator
		else:
			decorator(impl)

	def __call__(self, arg, *rest, **kwargs):
		impl = self.dispatch(arg)
		return impl(arg, *rest, **kwargs)

	def copy(self):
		return type(self)(self.default, dict(self.registry))


class SingleDispatch(SingleDispatchBase):
	"""Generic function which dispatches on the type of its first argument."""

	def validate_key(self, key):
		if not isinstance(key, type):
			raise TypeError('Keys must be types')
		return key

	def iter_keys(self, arg):
		return type(arg).mro()


def parse_iso_date(string):
	"""Parse date or datetime from an ISO 8601 date string.

	Parameters
	----------
	string

	Returns
	-------
	datetime.date or datetime.datetime
		Return time varies based on whether the string includes a time component.
	"""
	try:
		# Split into date[, time, timezone]
		match = re.fullmatch(r'([\d-]+)(?:T([\d:.]+)(.*))?', string)
		assert match, 'Bad format'
		datepart, timepart, tzpart = match.groups()

		# Parse date
		datematch = re.fullmatch(r'(\d\d\d\d)(?:-(\d\d)(?:-(\d\d))?)?', datepart)
		assert datematch, 'Bad date'
		year, month, day = [int(g or 1) for g in datematch.groups()]

		# Date only
		if not timepart:
			return date(year, month, day)

		# Parse time
		timematch = re.fullmatch(r'(\d\d)(?::(\d\d)(?::(\d\d)(?:\.(\d+))?)?)?', timepart)
		assert timematch, 'Bad time'
		hour, minute, second = [int(g or 0) for g in timematch.groups()[:3]]

		msecond = int(timematch.group(4)[:6].ljust(6, '0')) if timematch.group(4) else 0

		# Parse time zone
		if not tzpart:
			tz = None

		elif tzpart == 'Z':
			tz = timezone.utc

		else:
			tzmatch = re.fullmatch(r'[+-](\d\d):(\d\d)', tzpart)
			assert tzmatch, 'Bad time zone'
			tzhours, tzminutes = map(int, tzmatch.groups())
			td = timedelta(hours=tzhours, minutes=tzminutes)
			tz = timezone(td) if tzpart.startswith('+') else timezone(-td)

		return datetime(year, month, day, hour, minute, second, msecond, tzinfo=tz)


	except (ValueError, AssertionError):
		raise ValueError('Invalid ISO8601 time: ' + string) from None


class Namespace:
	"""A simple collection of attribute values, that supports inheritance.

	Meant to be used to pass large sets of arguments down through recursive
	function calls in a way that they can be overridden easily.

	Public attributes and methods start with an underscore so as not to
	interfere with the namespace.

	Attributes
	----------
	_map : collections.ChainMap
		Stores the underlying data.
	"""
	__slots__ = ('_map')

	def __init__(self, _map=None, **kwargs):
		if _map is None:
			_map = dict()
		if not isinstance(_map, ChainMap):
			_map = ChainMap(_map)

		_map.update(kwargs)
		self._map = _map

	def _flatten(self):
		"""Flatten into non-hierarchical format.

		Returns
		-------
		dict
		"""
		return dict(self._map)

	@property
	def _root(self):
		return Namespace(ChainMap(self._map.maps[-1]))

	def _push_map(self, _map, **kwargs):
		if _map is None:
			_map = dict()
		_map.update(kwargs)
		return self._map.new_child(_map)

	def _push(self, _map=None, **kwargs):
		"""Create a new namespace object that inherits from this one.

		Returns
		-------
		.Namespace
		"""
		return Namespace(self._push_map())

	def _pop(self):
		"""Get the namespace this one inherits from.

		Returns
		-------
		.Namespace
		"""
		return Namespace(self._map.parents)

	def _update(self, *args, **kwargs):
		self._map.update(*args, **kwargs)

	def __getattr__(self, name):
		if not name.startswith('_'):
			try:
				return self._map[name]
			except KeyError:
				pass

		raise AttributeError(name)

	def __setattr__(self, name, value):
		if not name.startswith('_'):
			self._map[name] = value
		else:
			object.__setattr__(self, name, value)

	def __getitem__(self, key):
		return self._map[key]

	def __setitem__(self, key, value):
		self._map[key] = value

	def __delitem__(self, key):
		del self._map[key]

	def __repr__(self):
		return '<%s %r>' % (type(self).__name__, self._flatten())


class TreeNamespace(Namespace):
	"""Namespace with a ``_path`` attribute that marks its location in a tree structure.

	Attributes
	----------
	_path : tuple
	"""
	__slots__ = ('_path')

	def __init__(self, _map=None, _path=(), **kwargs):
		super().__init__(_map, **kwargs)
		if len(_path) != len(self._map.maps) - 1:
			raise ValueError('Length of path does not match ChainMap depth')
		self._path = tuple(_path)

	def _push(self, _part, _map=None, **kwargs):
		childpath = self._path + (_part,)
		childmap = self._push_map(_map, **kwargs)
		return TreeNamespace(childmap, childpath)

	def _pop(self):
		return TreeNamespace(self._map.parents, self._path[:-1])

	@property
	def _root(self):
		return TreeNamespace(ChainMap(self._map.maps), ())
