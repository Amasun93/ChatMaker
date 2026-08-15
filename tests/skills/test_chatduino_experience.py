import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SKILL = ROOT / "skills" / "chatduino"


class TeacherExperienceContractTests(unittest.TestCase):
    def test_skill_requires_two_high_visibility_code_blocks(self):
        contract = (SKILL / "references" / "beginner-hardware-contract.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("## 🔌 接线说明（先断电）", contract)
        self.assertIn("## 💻 完整程序（可整段复制）", contract)
        self.assertIn("`text`", contract)
        self.assertIn("`cpp`", contract)
        self.assertIn("Do not create SVG", contract)

    def test_beginner_guidance_translates_jargon_with_analogies(self):
        guide = (SKILL / "references" / "nano-beginner-guidance.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("先说人话，再给专业名词", guide)
        self.assertIn("类比", guide)
        for term in ("VCC", "GND", "引脚", "编译", "烧录"):
            self.assertIn(term, guide)

    def test_photo_is_optional_and_unknown_parts_use_guided_questions(self):
        skill = (SKILL / "SKILL.md").read_text(encoding="utf-8")
        guide = (SKILL / "references" / "nano-beginner-guidance.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("照片不是必需条件", skill)
        self.assertIn("每轮只问 1-2 个", skill)
        self.assertIn("先问有几根针脚或几根线", guide)
        self.assertIn("再问针脚旁边写了哪些字母", guide)
        self.assertIn("照片只作为可选帮助", guide)

    def test_output_contract_keeps_wiring_and_code_in_fenced_blocks(self):
        contract = (SKILL / "references" / "nano-teacher-output-contract.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("## 🔌 接线说明（先断电）", contract)
        self.assertIn("紧跟一个 `text` 代码块", contract)
        self.assertIn("## 💻 完整程序（可整段复制）", contract)
        self.assertIn("紧跟一个 `cpp` 代码块", contract)

    def test_skill_defaults_to_compile_and_auto_upload(self):
        skill = (SKILL / "SKILL.md").read_text(encoding="utf-8")
        contract = (SKILL / "references" / "nano-teacher-output-contract.md").read_text(
            encoding="utf-8"
        )

        self.assertIn("默认调用 `nano_compile_upload`", skill)
        self.assertIn("不等待老师额外确认", skill)
        self.assertIn("最多自动修改并重试 2 次", skill)
        self.assertIn("未检测到硬件", contract)
        self.assertIn("接入 Nano 后自动上传", contract)

    def test_esp32_compile_upload_keeps_runtime_gates_separate(self):
        skill = (SKILL / "SKILL.md").read_text(encoding="utf-8")

        self.assertIn("`esp32_compile_upload`", skill)
        self.assertIn("`awaiting-hardware`", skill)
        self.assertIn("one non-Bluetooth wired port", skill)
        for gate in ("Wi-Fi AP", "HTTP exchange", "LED behavior", "sensor readings"):
            with self.subTest(gate=gate):
                self.assertIn(gate, skill)


if __name__ == "__main__":
    unittest.main()
