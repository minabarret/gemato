# gemato: CLI routines
# vim:fileencoding=utf-8
# (c) 2017 Michał Górny
# Licensed under the terms of 2-clause BSD license

from __future__ import print_function

import argparse
import datetime
import io
import logging
import os.path
import timeit

import gemato.find_top_level
import gemato.recursiveloader


def verify_warning(e):
    logging.warning(str(e))
    return True


def verify_failure(e):
    logging.error(str(e))
    return False


def do_verify(args, argp):
    ret = True

    for p in args.paths:
        tlm = gemato.find_top_level.find_top_level_manifest(p)
        if tlm is None:
            logging.error('Top-level Manifest not found in {}'.format(p))
            return 1

        init_kwargs = {}
        kwargs = {}
        if args.keep_going:
            kwargs['fail_handler'] = verify_failure
        if not args.strict:
            kwargs['warn_handler'] = verify_warning
        if not args.openpgp_verify:
            init_kwargs['verify_openpgp'] = False
        with gemato.openpgp.OpenPGPEnvironment() as env:
            if args.openpgp_key is not None:
                with io.open(args.openpgp_key, 'rb') as f:
                    env.import_key(f)
                init_kwargs['openpgp_env'] = env

            start = timeit.default_timer()
            try:
                m = gemato.recursiveloader.ManifestRecursiveLoader(tlm, **init_kwargs)
            except gemato.exceptions.OpenPGPNoImplementation as e:
                logging.error(str(e))
                return 1
            except gemato.exceptions.OpenPGPVerificationFailure as e:
                logging.error(str(e))
                return 1
            if args.require_signed_manifest and not m.openpgp_signed:
                logging.error('Top-level Manifest {} is not OpenPGP signed'.format(tlm))
                return 1

            relpath = os.path.relpath(p, os.path.dirname(tlm))
            if relpath == '.':
                relpath = ''
            try:
                ret &= m.assert_directory_verifies(relpath, **kwargs)
            except gemato.exceptions.ManifestCrossDevice as e:
                logging.error(str(e))
                return 1
            except gemato.exceptions.ManifestIncompatibleEntry as e:
                logging.error(str(e))
                return 1
            except gemato.exceptions.ManifestMismatch as e:
                logging.error(str(e))
                return 1

            stop = timeit.default_timer()
            logging.info('{} validated in {:.2f} seconds'.format(p, stop - start))
    return 0 if ret else 1


def do_update(args, argp):
    for p in args.paths:
        tlm = gemato.find_top_level.find_top_level_manifest(p)
        if tlm is None:
            logging.error('Top-level Manifest not found in {}'.format(p))
            return 1

        init_kwargs = {}
        init_kwargs['hashes'] = args.hashes.split()
        save_kwargs = {}
        save_kwargs['sort'] = True
        if args.compress_watermark is not None:
            if args.compress_watermark < 0:
                argp.error('--compress-watermark must not be negative!')
            save_kwargs['compress_watermark'] = args.compress_watermark
        if args.compress_format is not None:
            save_kwargs['compress_format'] = args.compress_format
        if args.force_rewrite:
            save_kwargs['force'] = True
        if args.openpgp_id is not None:
            init_kwargs['openpgp_keyid'] = args.openpgp_id
        if args.sign is not None:
            init_kwargs['sign_openpgp'] = args.sign
        with gemato.openpgp.OpenPGPEnvironment() as env:
            if args.openpgp_key is not None:
                with io.open(args.openpgp_key, 'rb') as f:
                    env.import_key(f)
                init_kwargs['openpgp_env'] = env

            start = timeit.default_timer()
            try:
                m = gemato.recursiveloader.ManifestRecursiveLoader(tlm,
                        **init_kwargs)
            except gemato.exceptions.OpenPGPNoImplementation as e:
                logging.error(str(e))
                return 1
            except gemato.exceptions.OpenPGPVerificationFailure as e:
                logging.error(str(e))
                return 1

            relpath = os.path.relpath(p, os.path.dirname(tlm))
            if relpath == '.':
                relpath = ''
            try:
                m.update_entries_for_directory(relpath)

                ts = m.find_timestamp()
                if ts is not None:
                    ts.ts = datetime.datetime.utcnow()

                m.save_manifests(**save_kwargs)
            except gemato.exceptions.ManifestCrossDevice as e:
                logging.error(str(e))
                return 1
            except gemato.exceptions.ManifestInvalidPath as e:
                logging.error(str(e))
                return 1

            stop = timeit.default_timer()
            logging.info('{} updated in {:.2f} seconds'.format(p, stop - start))
    return 0


def do_create(args, argp):
    for p in args.paths:
        init_kwargs = {}
        init_kwargs['allow_create'] = True
        init_kwargs['hashes'] = args.hashes.split()
        save_kwargs = {}
        save_kwargs['sort'] = True
        if args.compress_watermark is not None:
            if args.compress_watermark < 0:
                argp.error('--compress-watermark must not be negative!')
            save_kwargs['compress_watermark'] = args.compress_watermark
        if args.compress_format is not None:
            save_kwargs['compress_format'] = args.compress_format
        if args.force_rewrite:
            save_kwargs['force'] = True
        if args.openpgp_id is not None:
            init_kwargs['openpgp_keyid'] = args.openpgp_id
        if args.sign is not None:
            init_kwargs['sign_openpgp'] = args.sign
        with gemato.openpgp.OpenPGPEnvironment() as env:
            if args.openpgp_key is not None:
                with io.open(args.openpgp_key, 'rb') as f:
                    env.import_key(f)
                init_kwargs['openpgp_env'] = env

            start = timeit.default_timer()
            try:
                m = gemato.recursiveloader.ManifestRecursiveLoader(
                        p, **init_kwargs)
            except gemato.exceptions.OpenPGPNoImplementation as e:
                logging.error(str(e))
                return 1
            except gemato.exceptions.OpenPGPVerificationFailure as e:
                logging.error(str(e))
                return 1

            try:
                m.update_entries_for_directory()

                ts = m.find_timestamp()
                if ts is not None:
                    ts.ts = datetime.datetime.utcnow()

                m.save_manifests(**save_kwargs)
            except gemato.exceptions.ManifestCrossDevice as e:
                logging.error(str(e))
                return 1
            except gemato.exceptions.ManifestInvalidPath as e:
                logging.error(str(e))
                return 1

            stop = timeit.default_timer()
            logging.info('{} updated in {:.2f} seconds'.format(p, stop - start))
    return 0


def main(argv):
    argp = argparse.ArgumentParser(
            prog=argv[0],
            description='Gentoo Manifest Tool')
    subp = argp.add_subparsers()

    verify = subp.add_parser('verify',
            help='Verify one or more directories against Manifests')
    verify.add_argument('paths', nargs='*', default=['.'],
            help='Paths to verify (defaults to "." if none specified)')
    verify.add_argument('-k', '--keep-going', action='store_true',
            help='Continue reporting errors rather than terminating on the first failure')
    verify.add_argument('-K', '--openpgp-key',
            help='Use only the OpenPGP key(s) from a specific file')
    verify.add_argument('-P', '--no-openpgp-verify', action='store_false',
            dest='openpgp_verify',
            help='Disable OpenPGP verification of signed Manifests')
    verify.add_argument('-s', '--require-signed-manifest', action='store_true',
            help='Require that the top-level Manifest is OpenPGP signed')
    verify.add_argument('-S', '--no-strict', action='store_false',
            dest='strict',
            help='Do not fail on non-strict Manifest issues (MISC/OPTIONAL entries)')
    verify.set_defaults(func=do_verify)

    update = subp.add_parser('update',
            help='Update the Manifest entries for one or more directory trees')
    update.add_argument('paths', nargs='*', default=['.'],
            help='Paths to update (defaults to "." if none specified)')
    update.add_argument('-c', '--compress-watermark', type=int,
            help='Minimum Manifest size for files to be compressed')
    update.add_argument('-C', '--compress-format',
            help='Format for compressed files (e.g. "gz", "bz2"...)')
    update.add_argument('-f', '--force-rewrite', action='store_true',
            help='Force rewriting all the Manifests, even if they did not change')
    update.add_argument('-H', '--hashes', required=True,
            help='Whitespace-separated list of hashes to use')
    update.add_argument('-k', '--openpgp-id',
            help='Use the specified OpenPGP key (by ID or user)')
    update.add_argument('-K', '--openpgp-key',
            help='Use only the OpenPGP key(s) from a specific file')
    signgroup = update.add_mutually_exclusive_group()
    signgroup.add_argument('-s', '--sign', action='store_true',
            default=None,
            help='Force signing the top-level Manifest')
    signgroup.add_argument('-S', '--no-sign', action='store_false',
            dest='sign',
            help='Disable signing the top-level Manifest')
    update.set_defaults(func=do_update)

    create = subp.add_parser('create',
            help='Create a Manifest tree starting at the specified file')
    create.add_argument('paths', nargs='*', default=['Manifest'],
            help='Paths to create (defaults to "Manifest" if none specified)')
    create.add_argument('-c', '--compress-watermark', type=int,
            help='Minimum Manifest size for files to be compressed')
    create.add_argument('-C', '--compress-format',
            help='Format for compressed files (e.g. "gz", "bz2"...)')
    create.add_argument('-f', '--force-rewrite', action='store_true',
            help='Force rewriting all the Manifests, even if they did not change')
    create.add_argument('-H', '--hashes', required=True,
            help='Whitespace-separated list of hashes to use')
    create.add_argument('-k', '--openpgp-id',
            help='Use the specified OpenPGP key (by ID or user)')
    create.add_argument('-K', '--openpgp-key',
            help='Use only the OpenPGP key(s) from a specific file')
    signgroup = create.add_mutually_exclusive_group()
    signgroup.add_argument('-s', '--sign', action='store_true',
            default=None,
            help='Force signing the top-level Manifest')
    signgroup.add_argument('-S', '--no-sign', action='store_false',
            dest='sign',
            help='Disable signing the top-level Manifest')
    create.set_defaults(func=do_create)

    vals = argp.parse_args(argv[1:])
    return vals.func(vals, argp)
