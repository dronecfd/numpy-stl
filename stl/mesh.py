import numpy
import collections

from python_utils import logger

AREA_SIZE_THRESHOLD = 1e-6
VECTORS = 3
DIMENSIONS = 3
X = 0
Y = 1
Z = 2


class Mesh(logger.Logged, collections.Mapping):
    '''
    Mesh object with easy access to the vectors through v0, v1 and v2. An

    :param numpy.array data: The data for this mesh
    :param bool calculate_normals: Whehter to calculate the normals
    :param bool remove_empty_areas: Whether to remove triangles with 0 area
            (due to rounding errors for example)

    >>> data = numpy.zeros(10, dtype=Mesh.dtype)
    >>> mesh = Mesh(data, remove_empty_areas=False)
    >>> # Increment vector 0 item 0
    >>> mesh.v0[0] += 1
    >>> mesh.v1[0] += 2

    # Check item 0 (contains v0, v1 and v2)
    >>> mesh[0]
    array([ 1.,  1.,  1.,  2.,  2.,  2.,  0.,  0.,  0.], dtype=float32)
    >>> mesh.vectors[0]
    array([[ 1.,  1.,  1.],
           [ 2.,  2.,  2.],
           [ 0.,  0.,  0.]], dtype=float32)
    >>> mesh.v0[0]
    array([ 1.,  1.,  1.], dtype=float32)
    >>> mesh.points[0]
    array([ 1.,  1.,  1.,  2.,  2.,  2.,  0.,  0.,  0.], dtype=float32)
    >>> mesh.data[0]
    ([0.0, 0.0, 0.0], [[1.0, 1.0, 1.0], [2.0, 2.0, 2.0], [0.0, 0.0, 0.0]], [0])
    >>> mesh.x[0]
    array([ 1.,  2.,  0.], dtype=float32)

    >>> mesh[0] = 3
    >>> mesh[0]
    array([ 3.,  3.,  3.,  3.,  3.,  3.,  3.,  3.,  3.], dtype=float32)

    >>> len(mesh) == len(list(mesh))
    True
    >>> (mesh.min_ < mesh.max_).all()
    True
    >>> mesh.update_normals()
    >>> mesh.units.sum()
    0.0
    >>> mesh.v0[:] = mesh.v1[:] = mesh.v2[:] = 0
    >>> mesh.points.sum()
    0.0
    '''
    dtype = numpy.dtype([
        ('normals', numpy.float32, (3, )),
        ('vectors', numpy.float32, (3, 3)),
        ('attr', 'u2', (1, )),
    ])

    def __init__(self, data, calculate_normals=True, remove_empty_areas=True):
        super(Mesh, self).__init__()
        if remove_empty_areas:
            data = self.remove_empty_areas(data)

        self.data = data

        points = self.points = data['vectors']
        self.points.shape = data.size, 9
        self.x = points[:, X::3]
        self.y = points[:, Y::3]
        self.z = points[:, Z::3]
        self.v0 = data['vectors'][:, 0]
        self.v1 = data['vectors'][:, 1]
        self.v2 = data['vectors'][:, 2]
        self.normals = data['normals']
        self.vectors = data['vectors']
        self.attr = data['attr']

        if calculate_normals:
            self.update_normals()

    @classmethod
    def remove_empty_areas(cls, data):
        vectors = data['vectors']
        v0 = vectors[:, 0]
        v1 = vectors[:, 1]
        v2 = vectors[:, 2]
        normals = numpy.cross(v1 - v0, v2 - v0)
        areas = numpy.sqrt((normals ** 2).sum(axis=1))
        return data[areas > AREA_SIZE_THRESHOLD]

    def update_normals(self):
        '''Update the normals for all points'''
        self.normals[:] = numpy.cross(self.v1 - self.v0, self.v2 - self.v0)

    def update_min(self):
        self._min = self.vectors.min(axis=(0, 1))

    def update_max(self):
        self._max = self.vectors.max(axis=(0, 1))

    def update_areas(self):
        areas = .5 * numpy.sqrt((self.normals ** 2).sum(axis=1))
        self.areas = areas.reshape((areas.size, 1))

    def update_units(self):
        units = self.normals.copy()
        non_zero_areas = self.areas > 0
        areas = self.areas

        if non_zero_areas.any():
            non_zero_areas.shape = non_zero_areas.shape[0]
            areas = numpy.hstack((2 * areas[non_zero_areas],) * DIMENSIONS)
            units[non_zero_areas] /= areas

        self.units = units

    def _get_or_update(key):
        def _get(self):
            if not hasattr(self, '_%s' % key):
                getattr(self, 'update_%s' % key)()
            return getattr(self, '_%s' % key)

        return _get

    def _set(key):
        def _set(self, value):
            setattr(self, '_%s' % key, value)

        return _set

    min_ = property(_get_or_update('min'), _set('min'),
                    doc='Mesh minimum value')
    max_ = property(_get_or_update('max'), _set('max'),
                    doc='Mesh maximum value')
    areas = property(_get_or_update('areas'), _set('areas'),
                     doc='Mesh areas')
    units = property(_get_or_update('units'), _set('units'),
                     doc='Mesh unit vectors')

    def __getitem__(self, k):
        return self.points[k]

    def __setitem__(self, k, v):
        self.points[k] = v

    def __len__(self):
        return self.points.shape[0]

    def __iter__(self):
        for point in self.points:
            yield point

