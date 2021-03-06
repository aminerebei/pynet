# -*- coding: utf-8 -*-
##########################################################################
# NSAp - Copyright (C) CEA, 2020
# Distributed under the terms of the CeCILL-B license, as published by
# the CEA-CNRS-INRIA. Refer to the LICENSE file or to
# http://www.cecill.info/licences/Licence_CeCILL-B_V1-en.html
# for details.
##########################################################################

"""
Common functions to transform image.
Code: https://github.com/fepegar/torchio
"""

# Import
import numpy as np
from scipy.spatial.transform import Rotation
from scipy.ndimage import map_coordinates
from .transform import compose
from .transform import gaussian_random_field
from .transform import affine_flow
from .utils import interval


def affine(arr, rotation=10, translation=10, zoom=0.2, seed=None):
    """ Random affine transformation.

    Parameters
    ----------
    arr: array
        the input data.
    rotation: float or 2-uplet, default 10
        the rotation in degrees of the simulated movements. Larger
        values generate more distorted images.
    translation: float or 2-uplet, default 10
        the translation in voxel of the simulated movements. Larger
        values generate more distorted images.
    zoom: float, default 0.2
        the zooming magnitude. Larger values generate more distorted images.
    seed: int, default None
        seed to control random number generator.

    Returns
    -------
    transformed: array
        the transformed input data.
    """
    rotation = interval(rotation)
    translation = interval(translation)
    np.random.seed(seed)
    random_rotations = np.random.uniform(
        low=rotation[0], high=rotation[1], size=arr.ndim)
    np.random.seed(seed)
    random_translations = np.random.uniform(
        low=translation[0], high=translation[1], size=arr.ndim)
    np.random.seed(seed)
    random_zooms = np.random.uniform(
        low=(1 - zoom), high=(1 + zoom), size=arr.ndim)
    random_rotations = Rotation.from_euler(
        "xyz", random_rotations, degrees=True)
    random_rotations = random_rotations.as_dcm()
    affine = compose(random_translations, random_rotations, random_zooms)
    shape = arr.shape
    flow = affine_flow(affine, shape)
    locs = flow.reshape(len(shape), -1)
    transformed = map_coordinates(arr, locs, order=3, cval=0)
    return transformed.reshape(shape)


def flip(arr, axis=None, seed=None):
    """ Apply a random mirror flip.

    Parameters
    ----------
    arr: array
        the input data.
    axis: int, default None
        apply flip on the specified axis. If not specified, randomize the
        flip axis.
    seed: int, default None
        seed to control random number generator.

    Returns
    -------
    transformed: array
        the transformed input data.
    """
    if axis is None:
        np.random.seed(seed)
        axis = np.random.randint(low=0, high=arr.ndim, size=1)[0]
    return np.flip(arr, axis=axis)


def deformation(arr, max_displacement=4, alpha=3, seed=None):
    """ Apply dense random elastic deformation.

    Reference: Khanal B, Ayache N, Pennec X., Simulating Longitudinal
    Brain MRIs with Known Volume Changes and Realistic Variations in Image
    Intensity, Front Neurosci, 2017.

    Parameters
    ----------
    arr: array
        the input data.
    max_displacement: float, default 4
        the maximum displacement in voxel along each dimension. Larger
        values generate more distorted images.
    alpha: float, default 3
        the power of the power-law momentum distribution. Larger values
        genrate smoother fields.
    seed: int, default None
        seed to control random number generator.

    Returns
    -------
    transformed: array
        the transformed input data.
    """
    kwargs = {"seed": seed}
    flow_x = gaussian_random_field(
        arr.shape[:2], alpha=alpha, normalize=True, **kwargs)
    flow_x /= flow_x.max()
    flow_x = np.asarray([flow_x] * arr.shape[-1]).transpose(1, 2, 0)
    if seed is not None:
        kwargs = {"seed": seed + 2}
    flow_y = gaussian_random_field(
        arr.shape[:2], alpha=alpha, normalize=True, **kwargs)
    flow_y /= flow_y.max()
    flow_y = np.asarray([flow_y] * arr.shape[-1]).transpose(1, 2, 0)
    if seed is not None:
        kwargs = {"seed": seed + 4}
    flow_z = gaussian_random_field(
        arr.shape[:2], alpha=alpha, normalize=True, **kwargs)
    flow_z /= flow_z.max()
    flow_z = np.asarray([flow_z] * arr.shape[-1]).transpose(1, 2, 0)
    flow = np.asarray([flow_x, flow_y, flow_z])
    flow *= max_displacement
    ranges = [np.arange(size) for size in arr.shape]
    locs = np.asarray(np.meshgrid(*ranges)).transpose(0, 2, 1, 3).astype(float)
    locs += flow
    locs = locs.reshape(len(locs), -1)
    transformed = map_coordinates(arr, locs, order=3, cval=0)
    return transformed.reshape(arr.shape)


def padd(arr, shape, fill_value=0):
    """ Apply a padding.

    Parameters
    ----------
    arr: array
        the input data.
    shape: list of int
        the desired shape.
    fill_value: int, default 0
        the value used to fill the array.

    Returns
    -------
    transformed: array
        the transformed input data.
    """
    orig_shape = arr.shape
    padding = []
    for orig_i, final_i in zip(orig_shape, shape):
        shape_i = final_i - orig_i
        half_shape_i = shape_i // 2
        if shape_i % 2 == 0:
            padding.append((half_shape_i, half_shape_i))
        else:
            padding.append((half_shape_i, half_shape_i + 1))
    for cnt in range(len(arr.shape) - len(padding)):
        padding.append((0, 0))
    return np.pad(arr, padding, mode="constant", constant_values=fill_value)


def downsample(self, arr, scale):
    """ Apply a downsampling.

    Parameters
    ----------
    arr: array
        the input data.
    scale: int
        the downsampling scale factor in all directions.

    Returns
    -------
    transformed: array
        the transformed input data.
    """
    slices = []
    for cnt, orig_i in enumerate(arr.shape):
        if cnt == 3:
            break
        slices.append(slice(0, orig_i, scale))
    return arr[tuple(slices)]
