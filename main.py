import os
import argparse
import subprocess
from pathlib import Path
import xml.etree.ElementTree as ET


class DependencyVisualizer:
    def __init__(self, graph_tool_path, output_path, repo_url):
        self.graph_tool_path = Path(graph_tool_path)
        self.output_path = Path(output_path)
        self.repo_url = repo_url

    def get_pom_file_path(self, group_id, artifact_id, version):
        """
        Формирует путь к POM файлу в репозитории Maven.
        """
        group_path = group_id.replace(".", "/")
        return Path(f"{self.repo_url}/{group_path}/{artifact_id}/{version}/{artifact_id}-{version}.pom")

    def fetch_pom_file(self, group_id, artifact_id, version):
        """
        Загружает и парсит POM-файл для указанного артефакта.
        """
        pom_path = self.get_pom_file_path(group_id, artifact_id, version)
        if not pom_path.exists():
            raise FileNotFoundError(f"POM файл не найден по пути: {pom_path}")

        try:
            tree = ET.parse(pom_path)
            return tree.getroot()
        except ET.ParseError as e:
            raise ValueError(f"Ошибка парсинга POM файла: {e}")

    def parse_dependencies(self, pom_root):
        """
        Извлекает зависимости из POM файла.
        """
        dependencies = []
        for dependency in pom_root.findall(".//dependency"):
            group_id = dependency.find("groupId").text
            artifact_id = dependency.find("artifactId").text
            version = dependency.find("version")
            version = version.text if version is not None else "LATEST"
            dependencies.append((group_id, artifact_id, version))
        return dependencies

    def resolve_dependencies(self, group_id, artifact_id, version, resolved=None):
        """
        Рекурсивно разрешает зависимости Maven.
        """
        if resolved is None:
            resolved = {}

        package_name = f"{group_id}:{artifact_id}:{version}"
        if package_name in resolved:
            return resolved

        try:
            pom_root = self.fetch_pom_file(group_id, artifact_id, version)
            dependencies = self.parse_dependencies(pom_root)
            resolved[package_name] = dependencies

            for dep_group, dep_artifact, dep_version in dependencies:
                self.resolve_dependencies(dep_group, dep_artifact, dep_version, resolved)

        except FileNotFoundError:
            print(f"Предупреждение: POM файл для {package_name} не найден, пропускаем...")
        except Exception as e:
            print(f"Ошибка обработки {package_name}: {e}")

        return resolved

    def generate_mermaid(self, dependencies):
        """
        Генерирует Mermaid диаграмму из зависимостей.
        """
        mermaid_graph = "graph TD\n"
        for package, deps in dependencies.items():
            for dep_group, dep_artifact, dep_version in deps:
                dep_name = f"{dep_group}:{dep_artifact}:{dep_version}"
                mermaid_graph += f'  "{package}" --> "{dep_name}"\n'
        return mermaid_graph

    def save_graph_image(self, mermaid_code):
        """
        Сохраняет граф в формате PNG, используя указанный инструмент.
        """
        temp_file = self.output_path.with_suffix(".mmd")
        with open(temp_file, "w", encoding="utf-8") as f:
            f.write(mermaid_code)

        subprocess.run(
            [str(self.graph_tool_path), "-i", str(temp_file), "-o", str(self.output_path)],
            check=True
        )
        temp_file.unlink()

    def visualize(self, group_id, artifact_id, version):
        """
        Полный процесс: собирает зависимости, генерирует Mermaid код и сохраняет граф.
        """
        print("Сбор зависимостей...")
        dependencies = self.resolve_dependencies(group_id, artifact_id, version)
        print("Генерация Mermaid кода...")
        mermaid_code = self.generate_mermaid(dependencies)
        print("Сохранение графа...")
        self.save_graph_image(mermaid_code)
        print("Граф успешно сохранен в", self.output_path)


def main():
    parser = argparse.ArgumentParser(
        description="Визуализатор графа зависимостей Maven."
    )
    parser.add_argument("--graph-tool", required=True, help="Путь к программе для визуализации графов")
    parser.add_argument("--package", required=True, help="Имя анализируемого пакета (groupId:artifactId:version)")
    parser.add_argument("--output", required=True, help="Путь к файлу с изображением графа зависимостей")
    parser.add_argument("--repo-url", required=True, help="URL-адрес репозитория")

    args = parser.parse_args()
    group_id, artifact_id, version = args.package.split(":")
    visualizer = DependencyVisualizer(
        graph_tool_path=args.graph_tool,
        output_path=args.output,
        repo_url=args.repo_url,
    )
    visualizer.visualize(group_id, artifact_id, version)


if __name__ == "__main__":
    main()
