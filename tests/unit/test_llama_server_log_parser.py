from __future__ import annotations

from apmatia.lib.llama_server.log_parser import (
    parse_llama_server_log_file,
    parse_llama_server_log_text,
    parse_llama_server_log_turns,
    summarize_llama_server_status,
)


def test_llama_server_log_parser_extracts_prompt_and_generation_stats() -> None:
    sample_log = """
main: server is listening on http://0.0.0.0:8000
srv  params_from_: Chat format: peg-native
init: chat template, thinking = 1
slot launch_slot_: id  0 | task 220 | processing task, is_child = 0
slot update_slots: id  0 | task 220 | new prompt, n_ctx_slot = 96000, n_keep = 0, task.n_tokens = 951
slot update_slots: id  0 | task 220 | prompt processing progress, n_tokens = 947, batch.n_tokens = 256, progress = 0.995794
slot init_sampler: id  0 | task 220 | init sampler, took 0.24 ms, tokens: text = 951, total = 951
srv  log_server_r: done request: POST /v1/chat/completions 192.168.86.55 200
slot print_timing: id  0 | task 220 |
prompt eval time =    4670.03 ms /   951 tokens (    4.91 ms per token,   203.64 tokens per second)
       eval time =   26942.63 ms /   609 tokens (   44.24 ms per token,    22.60 tokens per second)
      total time =   31612.67 ms /  1560 tokens
slot      release: id  0 | task 220 | stop processing: n_tokens = 1559, truncated = 0
""".strip()

    status = parse_llama_server_log_text(sample_log)

    assert status.server_ready is True
    assert status.server_url == "http://0.0.0.0:8000"
    assert status.chat_format == "peg-native"
    assert status.thinking_enabled is True
    assert status.selected_slot_id == 0
    assert status.current_task_id == 220
    assert status.prompt_tokens_total == 951
    assert status.prompt_processing_progress == 0.995794
    assert status.prompt_processing_n_tokens == 947
    assert status.prompt_processing_batch_tokens == 256
    assert status.prompt_eval.tokens == 951
    assert status.prompt_eval.milliseconds == 4670.03
    assert status.prompt_eval.tokens_per_second == 203.64
    assert status.eval.tokens == 609
    assert status.eval.milliseconds == 26942.63
    assert status.eval.tokens_per_second == 22.6
    assert status.total_time_ms == 31612.67
    assert status.total_tokens == 1559
    assert status.truncated is False

    summary = summarize_llama_server_status(status)
    assert summary is not None
    assert "chat format peg-native" in summary
    assert "thinking on" in summary
    assert "slot 0 task 220" in summary
    assert "prompt 99.6%" in summary
    assert "prompt eval 203.64 tok/s" in summary
    assert "generation 22.60 tok/s" in summary
    assert "total 1559 tokens / 31.61s" in summary


def test_llama_server_log_parser_extracts_completed_turn_history() -> None:
    sample_log = """
main: server is listening on http://0.0.0.0:8000
srv  params_from_: Chat format: peg-native
init: chat template, thinking = 1
slot launch_slot_: id  0 | task 0 | processing task, is_child = 0
slot update_slots: id  0 | task 0 | prompt processing progress, n_tokens = 4, batch.n_tokens = 4, progress = 1.0
slot init_sampler: id  0 | task 0 | init sampler, took 0.24 ms, tokens: text = 4, total = 4
srv  log_server_r: done request: POST /v1/chat/completions 192.168.86.55 200
slot print_timing: id  0 | task 0 |
prompt eval time =    10.00 ms /     4 tokens (    2.50 ms per token,   400.00 tokens per second)
       eval time =    20.00 ms /     5 tokens (    4.00 ms per token,   250.00 tokens per second)
      total time =    30.00 ms /     9 tokens
slot      release: id  0 | task 0 | stop processing: n_tokens = 9, truncated = 0
slot launch_slot_: id  0 | task 1 | processing task, is_child = 0
slot update_slots: id  0 | task 1 | prompt processing progress, n_tokens = 5, batch.n_tokens = 1, progress = 1.0
slot init_sampler: id  0 | task 1 | init sampler, took 0.30 ms, tokens: text = 5, total = 5
srv  log_server_r: done request: POST /v1/chat/completions 192.168.86.55 200
slot print_timing: id  0 | task 1 |
prompt eval time =    11.00 ms /     5 tokens (    2.20 ms per token,   454.55 tokens per second)
       eval time =    22.00 ms /     6 tokens (    3.67 ms per token,   272.73 tokens per second)
      total time =    33.00 ms /    11 tokens
slot      release: id  0 | task 1 | stop processing: n_tokens = 11, truncated = 0
""".strip()

    turns = parse_llama_server_log_turns(sample_log)

    assert len(turns) == 2
    assert turns[0].current_task_id == 0
    assert turns[0].total_tokens == 9
    assert turns[0].eval.tokens_per_second == 250.0
    assert turns[1].current_task_id == 1
    assert turns[1].total_tokens == 11
    assert turns[1].eval.tokens_per_second == 272.73


def test_llama_server_log_parser_prefers_latest_file_in_directory(tmp_path) -> None:
    older = tmp_path / "older.txt"
    newer = tmp_path / "newer.txt"
    older.write_text(
        "main: server is listening on http://0.0.0.0:8000\nsrv  params_from_: Chat format: older\n",
        encoding="utf-8",
    )
    newer.write_text(
        "main: server is listening on http://0.0.0.0:8000\nsrv  params_from_: Chat format: newer\n",
        encoding="utf-8",
    )

    status = parse_llama_server_log_file(tmp_path)
    assert status is not None
    assert status.chat_format == "newer"
