"""Misc. utility code."""

from abc import ABC



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
		self.owner = type(instance) if owner is None else owner

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
		return SingleDispatchMethod(self, instance, owner)

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
