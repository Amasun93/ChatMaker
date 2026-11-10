import unittest
from unittest import mock

from chatmaker.hardware import workflow


class BoardBoundary:
    """Controlled hardware boundary; workflow decisions remain real."""
    def __init__(self, ready=True, prepare_success=True, stage='awaiting-hardware'):
        self.ready = ready
        self.prepare_success = prepare_success
        self.stage = stage
        self.actions = []

    def execute_request(self, request):
        self.actions.append(request['action'])
        if request['action'] == 'doctor':
            return {'ready_for_compile': self.ready, 'success': True}
        if request['action'] == 'prepare-environment':
            self.ready = self.prepare_success
            return {'success': self.prepare_success, 'error': None if self.ready else 'download_failed'}
        return {'success': False, 'stage': self.stage,
                'compile': {'success': True}, 'upload': {'success': False}}


class WorkflowTests(unittest.TestCase):
    def run_board(self, board, **kwargs):
        return workflow.run_project({'board_id': 'test-board', 'code': 'void setup(){} void loop(){}', **kwargs}, adapters={'test-board': board})

    def test_ready_environment_is_reused_without_preparation(self):
        board = BoardBoundary()
        result = self.run_board(board)
        self.assertEqual(board.actions, ['doctor', 'compile-upload'])
        self.assertTrue(result['code_compiled'])
        self.assertFalse(result['firmware_uploaded'])
        self.assertEqual(result['state'], 'compiled-awaiting-hardware')

    def test_missing_environment_is_prepared_once_and_reused_next_run(self):
        board = BoardBoundary(ready=False)
        self.run_board(board)
        self.run_board(board)
        self.assertEqual(board.actions, ['doctor', 'prepare-environment', 'compile-upload', 'doctor', 'compile-upload'])

    def test_preparation_failure_does_not_compile_or_try_another_backend(self):
        board = BoardBoundary(ready=False, prepare_success=False)
        result = self.run_board(board)
        self.assertEqual(board.actions, ['doctor', 'prepare-environment'])
        self.assertEqual(result['state'], 'awaiting-environment')
        self.assertEqual(result['environment']['error'], 'download_failed')

    def test_no_source_does_not_probe_or_install(self):
        board = BoardBoundary()
        result = workflow.run_project({'board_id': 'test-board'}, adapters={'test-board': board})
        self.assertEqual(result['state'], 'source-needed')
        self.assertEqual(board.actions, [])

    def test_failed_upload_is_never_reported_as_uploaded(self):
        result = self.run_board(BoardBoundary(stage='upload'))
        self.assertFalse(result['firmware_uploaded'])
        self.assertTrue(result['code_compiled'])
        self.assertFalse(result['physical_effect_verified'])

    def test_unknown_board_does_not_fall_back_to_generic_esp32(self):
        result = workflow.run_project({'board_id': 'unknown', 'code': 'x'}, adapters={})
        self.assertEqual(result['state'], 'unsupported-board')

    def test_existing_adapter_compile_failures_keep_the_compiler_evidence(self):
        failures = [
            {'success': False, 'stage': 'compile', 'compile': {'success': False, 'error': 'bad_source'}, 'upload': None},
            {'action': 'compile', 'success': False, 'error': 'bad_source'},
        ]
        for failure in failures:
            with self.subTest(failure=failure):
                adapter = mock.Mock()
                adapter.execute_request.side_effect = [{'ready_for_compile': True}, failure]
                result = self.run_board(adapter)
                self.assertEqual(result['state'], 'compile-failed')
                self.assertEqual(result['execution'], failure)
                self.assertFalse(result['firmware_uploaded'])

    def test_success_without_upload_evidence_is_not_reported_as_downloaded(self):
        adapter = mock.Mock()
        adapter.execute_request.side_effect = [
            {'ready_for_compile': True},
            {'action': 'compile', 'success': True},
        ]
        result = self.run_board(adapter)
        self.assertFalse(result['success'])
        self.assertNotEqual(result['state'], 'uploaded-awaiting-observation')

    def test_serial_evidence_uses_reenumerated_port_without_claiming_visible_effect(self):
        adapter = mock.Mock()
        adapter.execute_request.side_effect = [
            {'ready_for_compile': True},
            {'success': True, 'compile': {'success': True},
             'upload': {'success': True, 'port': 'COM2', 'application_port': 'COM9'}},
        ]
        with mock.patch.object(workflow, '_observe', return_value={'success': True, 'matched': True}) as observe:
            result = self.run_board(adapter, expected_serial_marker='RUNNING')
        self.assertEqual(observe.call_args.args[:2], ('COM9', 'RUNNING'))
        self.assertEqual(result['state'], 'runtime-observed')
        self.assertFalse(result['physical_effect_verified'])

