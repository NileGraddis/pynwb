import unittest2 as unittest
import six
from datetime import datetime
from dateutil.tz import tzlocal, tzutc
import os
from h5py import File

from pynwb import NWBFile, TimeSeries, get_manager, NWBHDF5IO

from hdmf.backends.hdf5 import HDF5IO, H5DataIO
from hdmf.data_utils import DataChunkIterator
from hdmf.build import GroupBuilder, DatasetBuilder
from hdmf.spec import NamespaceCatalog
from pynwb.spec import NWBGroupSpec, NWBDatasetSpec, NWBNamespace
from pynwb.ecephys import ElectricalSeries, LFP

import numpy as np


class TestHDF5Writer(unittest.TestCase):

    _required_tests = ('test_nwbio', 'test_write_clobber', 'test_write_cache_spec')

    @property
    def required_tests(self):
        return self._required_tests

    def setUp(self):
        self.manager = get_manager()
        self.path = "test_pynwb_io_hdf5.h5"
        self.start_time = datetime(1970, 1, 1, 12, tzinfo=tzutc())
        self.create_date = datetime(2017, 4, 15, 12, tzinfo=tzlocal())
        self.container = NWBFile('a test NWB File', 'TEST123',
                                 self.start_time, file_create_date=self.create_date)
        ts = TimeSeries('test_timeseries',
                        list(range(100, 200, 10)), 'SIunit', timestamps=list(range(10)), resolution=0.1)
        self.container.add_acquisition(ts)

        ts_builder = GroupBuilder('test_timeseries',
                                  attributes={'neurodata_type': 'TimeSeries',
                                              'help': 'General purpose TimeSeries'},
                                  datasets={'data': DatasetBuilder('data', list(range(100, 200, 10)),
                                                                   attributes={'unit': 'SIunit',
                                                                               'conversion': 1.0,
                                                                               'resolution': 0.1}),
                                            'timestamps': DatasetBuilder('timestamps', list(range(10)),
                                                                         attributes={'unit': 'Seconds',
                                                                                     'interval': 1})})
        self.builder = GroupBuilder(
            'root', groups={'acquisition': GroupBuilder('acquisition', groups={'test_timeseries': ts_builder}),
                            'analysis': GroupBuilder('analysis'),
                            'general': GroupBuilder('general'),
                            'processing': GroupBuilder('processing'),
                            'stimulus': GroupBuilder(
                                'stimulus',
                                groups={'presentation': GroupBuilder('presentation'),
                                        'templates': GroupBuilder('templates')})},
            datasets={'file_create_date': DatasetBuilder('file_create_date', [self.create_date.isoformat()]),
                      'identifier': DatasetBuilder('identifier', 'TEST123'),
                      'session_description': DatasetBuilder('session_description', 'a test NWB File'),
                      'nwb_version': DatasetBuilder('nwb_version', '1.0.6'),
                      'session_start_time': DatasetBuilder('session_start_time', self.start_time.isoformat())},
            attributes={'neurodata_type': 'NWBFile'})

    def tearDown(self):
        os.remove(self.path)

    def test_nwbio(self):
        io = HDF5IO(self.path, manager=self.manager, mode='a')
        io.write(self.container)
        io.close()
        f = File(self.path)
        self.assertIn('acquisition', f)
        self.assertIn('analysis', f)
        self.assertIn('general', f)
        self.assertIn('processing', f)
        self.assertIn('file_create_date', f)
        self.assertIn('identifier', f)
        self.assertIn('session_description', f)
        self.assertIn('session_start_time', f)
        acq = f.get('acquisition')
        self.assertIn('test_timeseries', acq)

    def test_write_clobber(self):
        io = HDF5IO(self.path, manager=self.manager, mode='a')
        io.write(self.container)
        io.close()
        f = File(self.path)  # noqa: F841

        if six.PY2:
            assert_file_exists = IOError
        elif six.PY3:
            assert_file_exists = OSError

        with self.assertRaises(assert_file_exists):
            io = HDF5IO(self.path, manager=self.manager, mode='w-')
            io.write(self.container)
            io.close()

    def test_write_cache_spec(self):
        '''
        Round-trip test for writing spec and reading it back in
        '''
        io = HDF5IO(self.path, manager=self.manager, mode="a")
        io.write(self.container, cache_spec=True)
        io.close()
        f = File(self.path)
        self.assertIn('specifications', f)
        ns_catalog = NamespaceCatalog(NWBGroupSpec, NWBDatasetSpec, NWBNamespace)
        HDF5IO.load_namespaces(ns_catalog, self.path, namespaces=['core'])
        original_ns = self.manager.namespace_catalog.get_namespace('core')
        cached_ns = ns_catalog.get_namespace('core')
        self.maxDiff = None
        for key in ('author', 'contact', 'doc', 'full_name', 'name'):
            with self.subTest(namespace_field=key):
                self.assertEqual(original_ns[key], cached_ns[key])
        for dt in original_ns.get_registered_types():
            with self.subTest(neurodata_type=dt):
                original_spec = original_ns.get_spec(dt)
                cached_spec = cached_ns.get_spec(dt)
                with self.subTest(test='data_type spec read back in'):
                    self.assertIsNotNone(cached_spec)
                with self.subTest(test='cached spec preserved original spec'):
                    self.assertDictEqual(original_spec, cached_spec)


class TestHDF5WriterWithInjectedFile(unittest.TestCase):

    _required_tests = ('test_nwbio', 'test_write_clobber', 'test_write_cache_spec')

    @property
    def required_tests(self):
        return self._required_tests

    def setUp(self):
        self.manager = get_manager()
        self.path = "test_pynwb_io_hdf5.h5"
        self.start_time = datetime(1970, 1, 1, 12, tzinfo=tzutc())
        self.create_date = datetime(2017, 4, 15, 12, tzinfo=tzlocal())
        self.container = NWBFile('a test NWB File', 'TEST123',
                                 self.start_time, file_create_date=self.create_date)
        ts = TimeSeries('test_timeseries',
                        list(range(100, 200, 10)), 'SIunit', timestamps=list(range(10)), resolution=0.1)
        self.container.add_acquisition(ts)

        ts_builder = GroupBuilder('test_timeseries',
                                  attributes={'neurodata_type': 'TimeSeries',
                                              'help': 'General purpose TimeSeries'},
                                  datasets={'data': DatasetBuilder('data', list(range(100, 200, 10)),
                                                                   attributes={'unit': 'SIunit',
                                                                               'conversion': 1.0,
                                                                               'resolution': 0.1}),
                                            'timestamps': DatasetBuilder('timestamps', list(range(10)),
                                                                         attributes={'unit': 'Seconds',
                                                                                     'interval': 1})})
        self.builder = GroupBuilder(
            'root', groups={'acquisition': GroupBuilder('acquisition', groups={'test_timeseries': ts_builder}),
                            'analysis': GroupBuilder('analysis'),
                            'general': GroupBuilder('general'),
                            'processing': GroupBuilder('processing'),
                            'stimulus': GroupBuilder(
                                'stimulus',
                                groups={'presentation': GroupBuilder('presentation'),
                                        'templates': GroupBuilder('templates')})},
            datasets={'file_create_date': DatasetBuilder('file_create_date', [self.create_date.isoformat()]),
                      'identifier': DatasetBuilder('identifier', 'TEST123'),
                      'session_description': DatasetBuilder('session_description', 'a test NWB File'),
                      'nwb_version': DatasetBuilder('nwb_version', '1.0.6'),
                      'session_start_time': DatasetBuilder('session_start_time', self.start_time.isoformat())},
            attributes={'neurodata_type': 'NWBFile'})

    def tearDown(self):
        os.remove(self.path)

    def test_nwbio(self):
        fil = File(self.path)
        io = HDF5IO(self.path, manager=self.manager, file=fil, mode="a")
        io.write(self.container)
        io.close()
        f = File(self.path)
        self.assertIn('acquisition', f)
        self.assertIn('analysis', f)
        self.assertIn('general', f)
        self.assertIn('processing', f)
        self.assertIn('file_create_date', f)
        self.assertIn('identifier', f)
        self.assertIn('session_description', f)
        self.assertIn('session_start_time', f)
        acq = f.get('acquisition')
        self.assertIn('test_timeseries', acq)

    def test_write_clobber(self):
        fil = File(self.path)
        io = HDF5IO(self.path, manager=self.manager, file=fil, mode="a")
        io.write(self.container)
        io.close()
        f = File(self.path)  # noqa: F841

        if six.PY2:
            assert_file_exists = IOError
        elif six.PY3:
            assert_file_exists = OSError

        with self.assertRaises(assert_file_exists):
            io = HDF5IO(self.path, manager=self.manager, mode='w-')
            io.write(self.container)
            io.close()

    def test_write_cache_spec(self):
        '''
        Round-trip test for writing spec and reading it back in
        '''

        fil = File(self.path)
        io = HDF5IO(self.path, manager=self.manager, file=fil, mode='a')
        io.write(self.container, cache_spec=True)
        io.close()
        f = File(self.path)
        self.assertIn('specifications', f)
        ns_catalog = NamespaceCatalog(NWBGroupSpec, NWBDatasetSpec, NWBNamespace)
        HDF5IO.load_namespaces(ns_catalog, self.path, namespaces=['core'])
        original_ns = self.manager.namespace_catalog.get_namespace('core')
        cached_ns = ns_catalog.get_namespace('core')
        self.maxDiff = None
        for key in ('author', 'contact', 'doc', 'full_name', 'name'):
            with self.subTest(namespace_field=key):
                self.assertEqual(original_ns[key], cached_ns[key])
        for dt in original_ns.get_registered_types():
            with self.subTest(neurodata_type=dt):
                original_spec = original_ns.get_spec(dt)
                cached_spec = cached_ns.get_spec(dt)
                with self.subTest(test='data_type spec read back in'):
                    self.assertIsNotNone(cached_spec)
                with self.subTest(test='cached spec preserved original spec'):
                    self.assertDictEqual(original_spec, cached_spec)


class TestAppend(unittest.TestCase):

    def test_append(self):

        FILENAME = 'test_append.nwb'

        nwb = NWBFile(session_description='hi', identifier='hi', session_start_time=datetime(1970, 1, 1, 12,
                                                                                             tzinfo=tzutc()))
        proc_mod = nwb.create_processing_module(name='test_proc_mod', description='')
        proc_inter = LFP(name='test_proc_dset')
        proc_mod.add_data_interface(proc_inter)
        device = nwb.create_device(name='test_device')
        e_group = nwb.create_electrode_group(
            name='test_electrode_group',
            description='',
            location='',
            device=device
        )
        nwb.add_electrode(x=0.0, y=0.0, z=0.0, imp=np.nan, location='', filtering='', group=e_group)
        electrodes = nwb.create_electrode_table_region(region=[0], description='')
        e_series = ElectricalSeries(
            name='test_device',
            electrodes=electrodes,
            data=np.ones(shape=(100,)),
            rate=10000.0,
        )
        proc_inter.add_electrical_series(e_series)

        with NWBHDF5IO(FILENAME, mode='w') as io:
            io.write(nwb)

        with NWBHDF5IO(FILENAME, mode='a') as io:
            nwb = io.read()
            elec = nwb.modules['test_proc_mod']['LFP'].electrical_series['test_device'].electrodes
            ts2 = ElectricalSeries(name='timeseries2', data=[4., 5., 6.], rate=1.0, electrodes=elec)
            nwb.add_acquisition(ts2)
            io.write(nwb)

        with NWBHDF5IO(FILENAME, mode='r') as io:
            nwb = io.read()
            np.testing.assert_equal(nwb.acquisition['timeseries2'].data[:], ts2.data)


class TestH5DataIO(unittest.TestCase):
    """
    Test that H5DataIO functions correctly on round trip with the HDF5IO backend
    """
    def setUp(self):
        self.nwbfile = NWBFile('a', 'b', datetime(1970, 1, 1, 12, tzinfo=tzutc()))
        self.path = "test_pynwb_io_hdf5_h5dataIO.h5"

    def tearDown(self):
        if(os.path.exists(self.path)):
            os.remove(self.path)

    def test_gzip_timestamps(self):
        ts = TimeSeries('ts_name', [1, 2, 3], 'A', timestamps=H5DataIO(np.array([1., 2., 3.]), compression='gzip'))
        self.nwbfile.add_acquisition(ts)
        with NWBHDF5IO(self.path, 'w') as io:
            io.write(self.nwbfile)
        # confirm that the dataset was indeed compressed
        infile = File(self.path, 'r')
        self.assertEquals(infile['/acquisition/ts_name/timestamps'].compression, 'gzip')

    def test_write_dataset_custom_compress(self):
        a = H5DataIO(np.arange(30).reshape(5, 2, 3),
                     compression='gzip',
                     compression_opts=5,
                     shuffle=True,
                     fletcher32=True)
        ts = TimeSeries('ts_name', a, 'A', timestamps=np.arange(5))
        self.nwbfile.add_acquisition(ts)
        with NWBHDF5IO(self.path, 'w') as io:
            io.write(self.nwbfile)
        infile = File(self.path, 'r')
        dset = infile['/acquisition/ts_name/data']
        self.assertTrue(np.all(dset[:] == a.data))
        self.assertEqual(dset.compression, 'gzip')
        self.assertEqual(dset.compression_opts, 5)
        self.assertEqual(dset.shuffle, True)
        self.assertEqual(dset.fletcher32, True)

    def test_write_dataset_custom_chunks(self):
        a = H5DataIO(np.arange(30).reshape(5, 2, 3),
                     chunks=(1, 1, 3))
        ts = TimeSeries('ts_name', a, 'A', timestamps=np.arange(5))
        self.nwbfile.add_acquisition(ts)
        with NWBHDF5IO(self.path, 'w') as io:
            io.write(self.nwbfile)
        infile = File(self.path, 'r')
        dset = infile['/acquisition/ts_name/data']
        self.assertTrue(np.all(dset[:] == a.data))
        self.assertEqual(dset.chunks, (1, 1, 3))

    def test_write_dataset_custom_fillvalue(self):
        a = H5DataIO(np.arange(20).reshape(5, 4), fillvalue=-1)
        ts = TimeSeries('ts_name', a, 'A', timestamps=np.arange(5))
        self.nwbfile.add_acquisition(ts)
        with NWBHDF5IO(self.path, 'w') as io:
            io.write(self.nwbfile)
        infile = File(self.path, 'r')
        dset = infile['/acquisition/ts_name/data']
        self.assertTrue(np.all(dset[:] == a.data))
        self.assertEqual(dset.fillvalue, -1)

    def test_write_dataset_datachunkiterator(self):
        a = np.arange(30).reshape(5, 2, 3)
        aiter = iter(a)
        daiter = DataChunkIterator.from_iterable(aiter, buffer_size=2)
        ts = TimeSeries('ts_name', daiter, 'A', timestamps=np.arange(5))
        self.nwbfile.add_acquisition(ts)
        with NWBHDF5IO(self.path, 'w') as io:
            io.write(self.nwbfile)
        infile = File(self.path, 'r')
        dset = infile['/acquisition/ts_name/data']
        self.assertListEqual(dset[:].tolist(), a.tolist())

    def test_write_dataset_datachunkiterator_with_compression(self):
        a = np.arange(30).reshape(5, 2, 3)
        aiter = iter(a)
        daiter = DataChunkIterator.from_iterable(aiter, buffer_size=2)
        wrapped_daiter = H5DataIO(data=daiter,
                                  compression='gzip',
                                  compression_opts=5,
                                  shuffle=True,
                                  fletcher32=True)
        ts = TimeSeries('ts_name', wrapped_daiter, 'A', timestamps=np.arange(5))
        self.nwbfile.add_acquisition(ts)
        with NWBHDF5IO(self.path, 'w') as io:
            io.write(self.nwbfile)
        infile = File(self.path, 'r')
        dset = infile['/acquisition/ts_name/data']
        self.assertEqual(dset.shape, a.shape)
        self.assertListEqual(dset[:].tolist(), a.tolist())
        self.assertEqual(dset.compression, 'gzip')
        self.assertEqual(dset.compression_opts, 5)
        self.assertEqual(dset.shuffle, True)
        self.assertEqual(dset.fletcher32, True)
