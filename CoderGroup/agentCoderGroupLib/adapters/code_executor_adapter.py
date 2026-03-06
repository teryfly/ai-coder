class CodeExecutorAdapter:
    def __init__(self, backup_enabled: bool = True, log_level: str = "INFO"):
        from codeAiExecutorLib import CodeExecutor, ExecutorConfig

        config = ExecutorConfig(backup_enabled=backup_enabled, log_level=log_level)
        self._executor = CodeExecutor(config=config)

    def write_code(self, root_dir: str, task_text: str) -> list[dict]:
        msgs = []
        for msg in self._executor.execute(root_dir, task_text):
            msgs.append(msg)
        return msgs

    def dry_run(self, root_dir: str, task_text: str) -> tuple[bool, str]:
        errors = []
        for msg in self._executor.execute(root_dir, task_text, dry_run=True):
            if msg.get("type") == "error":
                errors.append(msg.get("message", ""))
        if errors:
            return False, "\n".join(errors)
        return True, ""

    def execute_full(self, root_dir: str, task_text: str) -> dict:
        summary = {}
        for msg in self._executor.execute(root_dir, task_text):
            if msg.get("type") == "summary":
                summary = msg.get("data", {})
        return summary

    def rollback(self, root_dir: str, file_path: str) -> bool:
        result = self._executor.rollback_file(root_dir, file_path)
        return result.success
