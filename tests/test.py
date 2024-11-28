import unittest
from pathlib import Path
import xml.etree.ElementTree as ET
from unittest.mock import patch, mock_open, MagicMock
from main import DependencyVisualizer, sanitize_mermaid_name


class TestDependencyVisualizer(unittest.TestCase):

    def setUp(self):
        """
        Настройка тестовых данных и экземпляра DependencyVisualizer.
        """
        self.graph_tool_path = "mock_graph_tool"
        self.output_path = "mock_output_path"
        self.repo_url = "mock_repo_url"
        self.visualizer = DependencyVisualizer(
            graph_tool_path=self.graph_tool_path,
            output_path=self.output_path,
            repo_url=self.repo_url,
        )

    def test_get_pom_file_path(self):
        """
        Проверка правильности формирования пути к POM-файлу.
        """
        group_id = "com.example"
        artifact_id = "example-artifact"
        version = "1.0.0"
        expected_path = Path("mock_repo_url/com/example/1.0.0/example-artifact-1.0.0.pom")
        result_path = self.visualizer.get_pom_file_path(group_id, artifact_id, version)
        self.assertEqual(result_path, expected_path)

    def test_sanitize_mermaid_name(self):
        """
        Проверка преобразования имени узла в безопасный формат для Mermaid.
        """
        raw_name = "com.example:artifact-name:1.0.0"
        sanitized = sanitize_mermaid_name(raw_name)
        self.assertEqual(sanitized, "com_example_artifact_name_1_0_0")

    @patch("main.ET.parse")
    def test_fetch_pom_file(self, mock_et_parse):
        """
        Проверка обработки POM-файла.
        """
        mock_pom_path = Path("mock_repo_url/com/example/1.0.0/example-artifact-1.0.0.pom")
        mock_et_parse.return_value = MagicMock()
        with patch("pathlib.Path.exists", return_value=True):
            result = self.visualizer.fetch_pom_file("com.example", "example-artifact", "1.0.0")
            self.assertIsNotNone(result)
            mock_et_parse.assert_called_once_with(mock_pom_path)

    @patch("main.ET.parse")
    def test_parse_dependencies(self, mock_et_parse):
        """
        Проверка извлечения зависимостей из POM-файла.
        """
        xml_content = """
        <project xmlns="http://maven.apache.org/POM/4.0.0">
            <dependencies>
                <dependency>
                    <groupId>com.example</groupId>
                    <artifactId>example-lib</artifactId>
                    <version>1.0.0</version>
                </dependency>
                <dependency>
                    <groupId>org.example</groupId>
                    <artifactId>example-utils</artifactId>
                    <version>2.0.0</version>
                </dependency>
            </dependencies>
        </project>
        """
        with patch("builtins.open", mock_open(read_data=xml_content)):
            root = ET.fromstring(xml_content)
            dependencies = self.visualizer.parse_dependencies(root)
            expected = [
                ("com.example", "example-lib", "1.0.0"),
                ("org.example", "example-utils", "2.0.0"),
            ]
            self.assertEqual(dependencies, expected)

    def test_generate_mermaid(self):
        """
        Проверка генерации Mermaid-кода.
        """
        dependencies = {
            "com.example:example-artifact:1.0.0": [
                ("com.example", "example-lib", "1.0.0"),
                ("org.example", "example-utils", "2.0.0"),
            ]
        }
        mermaid_code = self.visualizer.generate_mermaid(dependencies)
        expected_code = (
            "graph TD\n"
            "  com_example_example_artifact_1_0_0 --> com_example_example_lib_1_0_0\n"
            "  com_example_example_artifact_1_0_0 --> org_example_example_utils_2_0_0\n"
        )
        self.assertEqual(mermaid_code.strip(), expected_code.strip())

    @patch("subprocess.run")
    @patch("builtins.open", new_callable=mock_open)
    @patch("pathlib.Path.unlink", MagicMock())  # Заглушаем удаление файла
    def test_save_graph_image(self, mock_file, mock_run):
        """
        Проверка сохранения графа с использованием mmdc.
        """
        mermaid_code = "graph TD\n  com_example_example_artifact_1_0_0 --> com_example_example_lib_1_0_0\n"
        temp_file = self.visualizer.output_path.with_suffix(".mmd")

        # Вызываем метод сохранения графа
        self.visualizer.save_graph_image(mermaid_code)

        # Проверяем, что файл был создан
        mock_file.assert_called_once_with(temp_file, "w", encoding="utf-8")
        mock_file().write.assert_called_once_with(mermaid_code)

        # Проверяем, что mmdc был вызван
        mock_run.assert_called_once_with(
            [str(self.visualizer.graph_tool_path), "-i", str(temp_file), "-o", str(self.visualizer.output_path)],
            check=True
        )

    @patch("main.DependencyVisualizer.resolve_dependencies")
    @patch("main.DependencyVisualizer.generate_mermaid")
    @patch("main.DependencyVisualizer.save_graph_image")
    def test_visualize(self, mock_save_graph, mock_generate_mermaid, mock_resolve_dependencies):
        """
        Проверка полного процесса визуализации.
        """
        mock_resolve_dependencies.return_value = {
            "com.example:example-artifact:1.0.0": [
                ("com.example", "example-lib", "1.0.0")
            ]
        }
        mock_generate_mermaid.return_value = "graph TD\n  A --> B\n"

        self.visualizer.visualize("com.example", "example-artifact", "1.0.0")

        mock_resolve_dependencies.assert_called_once_with("com.example", "example-artifact", "1.0.0")
        mock_generate_mermaid.assert_called_once()
        mock_save_graph.assert_called_once_with("graph TD\n  A --> B\n")


if __name__ == "__main__":
    unittest.main()
