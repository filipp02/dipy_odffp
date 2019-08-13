import os
import numpy as np
import numpy.testing as npt
from dipy.testing import (assert_true, assert_false, assert_greater,
                          assert_less)

import nibabel as nib
from nibabel.tmpdirs import TemporaryDirectory

from dipy.data import get_fnames
from dipy.io.image import load_nifti, save_nifti
from dipy.workflows.denoise import (NLMeansFlow, LPCAFlow, MPPCAFlow,
                                    GibbsRingingFlow)


def test_nlmeans_flow():
    with TemporaryDirectory() as out_dir:
        data_path, _, _ = get_fnames()
        vol_img = nib.load(data_path)
        volume = vol_img.get_data()

        nlmeans_flow = NLMeansFlow()

        nlmeans_flow.run(data_path, out_dir=out_dir)
        assert_true(os.path.isfile(
                nlmeans_flow.last_generated_outputs['out_denoised']))

        nlmeans_flow._force_overwrite = True
        nlmeans_flow.run(data_path, sigma=4, out_dir=out_dir)
        denoised_path = nlmeans_flow.last_generated_outputs['out_denoised']
        assert_true(os.path.isfile(denoised_path))
        denoised_img = nib.load(denoised_path)
        denoised_data = denoised_img.get_data()
        npt.assert_equal(denoised_data.shape, volume.shape)
        npt.assert_array_almost_equal(denoised_img.affine, vol_img.affine)


def test_lpca_flow():
    with TemporaryDirectory() as out_dir:
        data_path, fbvals, fbvecs = get_fnames()
        vol_img = nib.load(data_path)
        volume = vol_img.get_data()

        lpca_flow = LPCAFlow()
        lpca_flow.run(data_path, fbvals, fbvecs, out_dir=out_dir)
        assert_true(os.path.isfile(
                lpca_flow.last_generated_outputs['out_denoised']))


def test_mppca_flow():
    with TemporaryDirectory() as out_dir:
        S0 = 100 + 2 * np.random.standard_normal((22, 23, 30, 20))
        data_path = os.path.join(out_dir, "random_noise.nii.gz")
        save_nifti(data_path, S0, np.eye(4))

        mppca_flow = MPPCAFlow()
        mppca_flow.run(data_path, out_dir=out_dir)
        assert_true(os.path.isfile(
                mppca_flow.last_generated_outputs['out_denoised']))
        assert_false(os.path.isfile(
                mppca_flow.last_generated_outputs['out_sigma']))

        mppca_flow._force_overwrite = True
        mppca_flow.run(data_path, return_sigma=True, pca_method='svd',
                       out_dir=out_dir)
        assert_true(os.path.isfile(
                mppca_flow.last_generated_outputs['out_denoised']))
        assert_true(os.path.isfile(
                mppca_flow.last_generated_outputs['out_sigma']))

        denoised_path = mppca_flow.last_generated_outputs['out_denoised']
        denoised_img = nib.load(denoised_path)
        denoised_data = denoised_img.get_data()
        assert_greater(denoised_data.min(), S0.min())
        assert_less(denoised_data.max(), S0.max())
        npt.assert_equal(np.round(denoised_data.mean()), 100)


def test_gibbs_flow():
    def generate_slice():
        Nori = 32
        image = np.zeros((6 * Nori, 6 * Nori))
        image[Nori: 2 * Nori, Nori: 2 * Nori] = 1
        image[Nori: 2 * Nori, 4 * Nori: 5 * Nori] = 1
        image[2 * Nori: 3 * Nori, Nori: 3 * Nori] = 1
        image[3 * Nori: 4 * Nori, 2 * Nori: 3 * Nori] = 2
        image[3 * Nori: 4 * Nori, 4 * Nori: 5 * Nori] = 1
        image[4 * Nori: 5 * Nori, 3 * Nori: 5 * Nori] = 3

        # Corrupt image with gibbs ringing
        c = np.fft.fft2(image)
        c = np.fft.fftshift(c)
        c_crop = c[48:144, 48:144]
        image_gibbs = abs(np.fft.ifft2(c_crop)/4)
        return image_gibbs

    with TemporaryDirectory() as out_dir:
        image4d = np.zeros((96, 96, 2, 2))
        image4d[:, :, 0, 0] = generate_slice()
        image4d[:, :, 1, 0] = generate_slice()
        image4d[:, :, 0, 1] = generate_slice()
        image4d[:, :, 1, 1] = generate_slice()
        data_path = os.path.join(out_dir, "random_noise.nii.gz")
        save_nifti(data_path, image4d, np.eye(4))

        gibbs_flow = GibbsRingingFlow()
        gibbs_flow.run(data_path, out_dir=out_dir)
        assert_true(os.path.isfile(
                gibbs_flow.last_generated_outputs['out_unring']))


if __name__ == '__main__':
    test_gibbs_flow()
    test_mppca_flow()
    test_lpca_flow()
    test_nlmeans_flow()
