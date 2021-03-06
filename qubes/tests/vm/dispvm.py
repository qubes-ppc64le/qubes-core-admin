# -*- encoding: utf-8 -*-
#
# The Qubes OS Project, http://www.qubes-os.org
#
# Copyright (C) 2017 Marek Marczykowski-Górecki
#                               <marmarek@invisiblethingslab.com>
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, see <https://www.gnu.org/licenses/>.

import unittest.mock as mock

import asyncio

import qubes.vm.dispvm
import qubes.vm.appvm
import qubes.vm.templatevm
import qubes.tests
import qubes.tests.vm
import qubes.tests.vm.appvm

class TestApp(qubes.tests.vm.TestApp):
    def __init__(self):
        super(TestApp, self).__init__()
        self.qid_counter = 1

    def add_new_vm(self, cls, **kwargs):
        qid = self.qid_counter
        self.qid_counter += 1
        vm = cls(self, None, qid=qid, **kwargs)
        self.domains[vm.name] = vm
        self.domains[vm] = vm
        return vm

class TC_00_DispVM(qubes.tests.QubesTestCase):
    def setUp(self):
        super(TC_00_DispVM, self).setUp()
        self.app = TestApp()
        self.app.save = mock.Mock()
        self.app.pools['default'] = qubes.tests.vm.appvm.TestPool(name='default')
        self.app.pools['linux-kernel'] = mock.Mock(**{
            'init_volume.return_value.pool': 'linux-kernel'})
        self.app.vmm.offline_mode = True
        self.template = self.app.add_new_vm(qubes.vm.templatevm.TemplateVM,
            name='test-template', label='red')
        self.appvm = self.app.add_new_vm(qubes.vm.appvm.AppVM,
            name='test-vm', template=self.template, label='red')
        self.app.domains[self.appvm.name] = self.appvm
        self.app.domains[self.appvm] = self.appvm
        self.addCleanup(self.cleanup_dispvm)

    def cleanup_dispvm(self):
        self.template.close()
        self.appvm.close()
        del self.template
        del self.appvm
        self.app.domains.clear()
        self.app.pools.clear()

    @asyncio.coroutine
    def mock_coro(self, *args, **kwargs):
        pass

    @mock.patch('os.symlink')
    @mock.patch('os.makedirs')
    @mock.patch('qubes.storage.Storage')
    def test_000_from_appvm(self, mock_storage, mock_makedirs, mock_symlink):
        mock_storage.return_value.create.side_effect = self.mock_coro
        self.appvm.template_for_dispvms = True
        orig_getitem = self.app.domains.__getitem__
        with mock.patch.object(self.app, 'domains', wraps=self.app.domains) \
                as mock_domains:
            mock_domains.configure_mock(**{
                'get_new_unused_dispid': mock.Mock(return_value=42),
                '__getitem__.side_effect': orig_getitem
            })
            dispvm = self.loop.run_until_complete(
                qubes.vm.dispvm.DispVM.from_appvm(self.appvm))
            mock_domains.get_new_unused_dispid.assert_called_once_with()
        self.assertEqual(dispvm.name, 'disp42')
        self.assertEqual(dispvm.template, self.appvm)
        self.assertEqual(dispvm.label, self.appvm.label)
        self.assertEqual(dispvm.label, self.appvm.label)
        self.assertEqual(dispvm.auto_cleanup, True)
        mock_makedirs.assert_called_once_with(
            '/var/lib/qubes/appvms/' + dispvm.name, mode=0o775, exist_ok=True)
        mock_symlink.assert_not_called()

    def test_001_from_appvm_reject_not_allowed(self):
        with self.assertRaises(qubes.exc.QubesException):
            dispvm = self.loop.run_until_complete(
                qubes.vm.dispvm.DispVM.from_appvm(self.appvm))

    def test_002_template_change(self):
        self.appvm.template_for_dispvms = True
        orig_getitem = self.app.domains.__getitem__
        with mock.patch.object(self.app, 'domains', wraps=self.app.domains) \
                as mock_domains:
            mock_domains.configure_mock(**{
                'get_new_unused_dispid': mock.Mock(return_value=42),
                '__getitem__.side_effect': orig_getitem
            })
            dispvm = self.app.add_new_vm(qubes.vm.dispvm.DispVM,
                name='test-dispvm', template=self.appvm)

            with self.assertRaises(qubes.exc.QubesValueError):
                dispvm.template = self.appvm
            with self.assertRaises(qubes.exc.QubesValueError):
                dispvm.template = qubes.property.DEFAULT


    def test_010_create_direct(self):
        self.appvm.template_for_dispvms = True
        orig_getitem = self.app.domains.__getitem__
        with mock.patch.object(self.app, 'domains', wraps=self.app.domains) \
                as mock_domains:
            mock_domains.configure_mock(**{
                'get_new_unused_dispid': mock.Mock(return_value=42),
                '__getitem__.side_effect': orig_getitem
            })
            dispvm = self.app.add_new_vm(qubes.vm.dispvm.DispVM,
                name='test-dispvm', template=self.appvm)
            mock_domains.get_new_unused_dispid.assert_called_once_with()
        self.assertEqual(dispvm.name, 'test-dispvm')
        self.assertEqual(dispvm.template, self.appvm)
        self.assertEqual(dispvm.label, self.appvm.label)
        self.assertEqual(dispvm.label, self.appvm.label)
        self.assertEqual(dispvm.auto_cleanup, False)

    def test_011_create_direct_generate_name(self):
        self.appvm.template_for_dispvms = True
        orig_getitem = self.app.domains.__getitem__
        with mock.patch.object(self.app, 'domains', wraps=self.app.domains) \
                as mock_domains:
            mock_domains.configure_mock(**{
                'get_new_unused_dispid': mock.Mock(return_value=42),
                '__getitem__.side_effect': orig_getitem
            })
            dispvm = self.app.add_new_vm(qubes.vm.dispvm.DispVM,
                template=self.appvm)
            mock_domains.get_new_unused_dispid.assert_called_once_with()
        self.assertEqual(dispvm.name, 'disp42')
        self.assertEqual(dispvm.template, self.appvm)
        self.assertEqual(dispvm.label, self.appvm.label)
        self.assertEqual(dispvm.auto_cleanup, False)

    def test_011_create_direct_reject(self):
        orig_getitem = self.app.domains.__getitem__
        with mock.patch.object(self.app, 'domains', wraps=self.app.domains) \
                as mock_domains:
            mock_domains.configure_mock(**{
                'get_new_unused_dispid': mock.Mock(return_value=42),
                '__getitem__.side_effect': orig_getitem
            })
            with self.assertRaises(qubes.exc.QubesException):
                self.app.add_new_vm(qubes.vm.dispvm.DispVM,
                    name='test-dispvm', template=self.appvm)
            self.assertFalse(mock_domains.get_new_unused_dispid.called)

    @mock.patch('os.symlink')
    @mock.patch('os.makedirs')
    def test_020_copy_storage_pool(self, mock_makedirs, mock_symlink):
        self.app.pools['alternative'] = qubes.tests.vm.appvm.TestPool(name='alternative')
        self.appvm.template_for_dispvms = True
        self.loop.run_until_complete(self.template.create_on_disk())
        self.loop.run_until_complete(self.appvm.create_on_disk(pool='alternative'))
        orig_getitem = self.app.domains.__getitem__
        with mock.patch.object(self.app, 'domains', wraps=self.app.domains) \
                as mock_domains:
            mock_domains.configure_mock(**{
                'get_new_unused_dispid': mock.Mock(return_value=42),
                '__getitem__.side_effect': orig_getitem
            })
            dispvm = self.app.add_new_vm(qubes.vm.dispvm.DispVM,
                name='test-dispvm', template=self.appvm)
            self.loop.run_until_complete(dispvm.create_on_disk())
        self.assertEqual(dispvm.template, self.appvm)
        self.assertEqual(dispvm.volumes['private'].pool,
                         self.appvm.volumes['private'].pool)
        self.assertEqual(dispvm.volumes['root'].pool,
                         self.appvm.volumes['root'].pool)
        self.assertEqual(dispvm.volumes['volatile'].pool,
                         self.appvm.volumes['volatile'].pool)
