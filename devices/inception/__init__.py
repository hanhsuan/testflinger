# Copyright (C) 2015 Canonical
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""Inception x86 support code."""

import logging
import multiprocessing
import subprocess
import yaml

import guacamole

import snappy_device_agents
from devices.inception.inception import Inception

device_name = "inception"


class provision(guacamole.Command):

    """Tool for provisioning x86 baremetal with a given image."""

    def invoked(self, ctx):
        """Method called when the command is invoked."""
        device = Inception(ctx.args.config)
        logging.info("ensure_master_image")
        device.ensure_master_image()
        image = snappy_device_agents.get_image(ctx.args.spi_data)
        server_ip = snappy_device_agents.get_local_ip_addr()
        test_username = snappy_device_agents.get_test_username(
            ctx.args.spi_data)
        test_password = snappy_device_agents.get_test_password(
            ctx.args.spi_data)
        q = multiprocessing.Queue()
        file_server = multiprocessing.Process(
            target=snappy_device_agents.serve_file, args=(q, image,))
        file_server.start()
        server_port = q.get()
        logging.info("flash_test_image")
        device.flash_test_image(server_ip, server_port)
        file_server.terminate()
        logging.info("ensure_test_image")
        device.ensure_test_image(test_username, test_password)

    def register_arguments(self, parser):
        """Method called to customize the argument parser."""
        parser.add_argument('-c', '--config', required=True,
                            help='Config file for this device')
        parser.add_argument('spi_data', help='SPI json data file')


class runtest(guacamole.Command):

    """Tool for running tests on a provisioned device."""

    def invoked(self, ctx):
        """Method called when the command is invoked."""
        with open(ctx.args.config) as configfile:
            config = yaml.load(configfile)

        test_opportunity = snappy_device_agents.get_test_opportunity(
            ctx.args.spi_data)
        test_cmds = test_opportunity.get('test_payload').get('test_cmds')
        for cmd in test_cmds:
            # Settings from the device yaml configfile like device_ip can be
            # formatted in test commands like "foo {device_ip}"
            try:
                cmd = cmd.format(**config)
            except:
                logging.error("Unable to format command: %s", cmd)

            logging.info("Running: %s", cmd)
            proc = subprocess.Popen(cmd, shell=True)
            proc.wait()

    def register_arguments(self, parser):
        """Method called to customize the argument parser."""
        parser.add_argument('-c', '--config', required=True,
                            help='Config file for this device')
        parser.add_argument('spi_data', help='SPI json data file')


class DeviceAgent(guacamole.Command):

    """Device agent for Inception x86."""

    sub_commands = (
        ('provision', provision),
        ('runtest', runtest),
    )
