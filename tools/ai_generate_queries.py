#!/usr/bin/env python3
import argparse
import oead
from pathlib import Path
import textwrap


def sort_params(params: list) -> list:
    def sort_by_type(param):
        t = param["Type"]
        if t == "String":
            return 1
        return 0

    return sorted(params, key=sort_by_type)


def generate_query_loadparam_body(query: dict, is_evfl: bool) -> str:
    if not query:
        return ""

    out = []

    if is_evfl:
        for param in sort_params(query.get("DynamicInstParams", [])):
            out.append(f"load{param['Type']}(arg.param_accessor, \"{param['Name']}\");")
    else:
        for param in sort_params(query.get("StaticInstParams", [])):
            out.append(f"getStaticParam(&m{param['Name']}, \"{param['Name']}\");")

        for param in sort_params(query.get("DynamicInstParams", [])):
            out.append(f"getDynamicParam(&m{param['Name']}, \"{param['Name']}\");")

        for param in sort_params(query.get("AITreeVariables", [])):
            out.append(f"getAITreeVariable(&m{param['Name']}, \"{param['Name']}\");")

    return "\n".join(out)


_types_static = {
    "Bool": "const bool*",
    "Int": "const int*",
    "Float": "const float*",
    "String": "sead::SafeString",
}

_types_dynamic = {
    "Bool": "bool*",
    "Int": "int*",
    "Float": "float*",
    "String": "sead::SafeString",
}

_types_ai_tree_var = {
    "String": "sead::SafeString*",
    "AITreeVariablePointer": "void*",
}


def generate_query_param_member_vars(query: dict) -> str:
    out = []

    for param in sort_params(query.get("StaticInstParams", [])):
        out.append(f"{_types_static[param['Type']]} m{param['Name']}{{}};")

    for param in sort_params(query.get("DynamicInstParams", [])):
        out.append(f"{_types_dynamic[param['Type']]} m{param['Name']}{{}};")

    for param in sort_params(query.get("AITreeVariables", [])):
        out.append(f"{_types_ai_tree_var[param['Type']]} m{param['Name']}{{}};")

    return "\n".join(out)


def generate_query(class_dir: Path, name: str, query) -> None:
    has_params = False
    if query != "":
        assert isinstance(query, oead.byml.Hash)
        query = dict(query)
        has_params = "DynamicInstParams" in query or "StaticInstParams" in query or "AITreeVariables" in query

    cpp_class_name = f"{name}"
    header_file_name = f"query{name}.h"

    # Header
    out = []
    out.append("#pragma once")
    out.append("")
    out.append('#include "KingSystem/ActorSystem/actAiQuery.h"')
    out.append("")
    out.append("namespace uking::query {")
    out.append("")
    out.append(f"class {cpp_class_name} : public ksys::act::ai::Query {{")
    out.append(f"    SEAD_RTTI_OVERRIDE({cpp_class_name}, Query)")
    out.append("public:")
    out.append(f"    explicit {cpp_class_name}(const InitArg& arg);")
    out.append(f"    ~{cpp_class_name}() override;")
    out.append(f"    int doQuery() override;")
    out.append("")
    out.append("    void loadParams() override;")
    out.append("    void loadParams(const evfl::QueryArg& arg) override;")
    if has_params:
        out.append("")
        out.append("protected:")
        out.append(textwrap.indent(generate_query_param_member_vars(query), " " * 4))
    out.append("};")  # =================================== end of class
    out.append("")
    out.append("}  // namespace uking::query")
    out.append("")
    (class_dir / header_file_name).write_text("\n".join(out))

    # .cpp
    out = []
    out.append(f'#include "Game/AI/Query/{header_file_name}"')
    out.append(f'#include <evfl/query.h>')
    out.append("")
    out.append("namespace uking::query {")
    out.append("")
    out.append(f"{cpp_class_name}::{cpp_class_name}(const InitArg& arg) : ksys::act::ai::Query(arg) {{}}")
    out.append("")
    out.append(f"{cpp_class_name}::~{cpp_class_name}() = default;")
    out.append("")
    out.append("// FIXME: implement")
    out.append(f"int {cpp_class_name}::doQuery() {{ return -1; }}")
    out.append("")
    out.append(f"void {cpp_class_name}::loadParams(const evfl::QueryArg& arg) {{")
    out.append(textwrap.indent(generate_query_loadparam_body(query, is_evfl=True), " " * 4))
    out.append(f"}}")
    out.append("")
    out.append(f"void {cpp_class_name}::loadParams() {{")
    out.append(textwrap.indent(generate_query_loadparam_body(query, is_evfl=False), " " * 4))
    out.append(f"}}")
    out.append("")
    out.append("}  // namespace uking::query")
    out.append("")
    (class_dir / f"query{name}.cpp").write_text("\n".join(out))


def main() -> None:
    src_root = Path(__file__).parent.parent
    class_dir = src_root / "src" / "Game" / "AI" / "Query"
    class_dir.mkdir(exist_ok=True)

    parser = argparse.ArgumentParser(description="Generates stubs for AI queries.")
    parser.add_argument("aidef")
    args = parser.parse_args()

    aidef = oead.byml.from_text(Path(args.aidef).read_text(encoding="utf-8"))

    count = 0
    keys = set()
    for query_name, data in aidef["Querys"].items():
        if isinstance(data, oead.byml.Hash) and dict(data).get("SystemQuery", False):
            continue

        if isinstance(data, oead.byml.Hash):
            keys |= set(data.keys())

        query_name = query_name[0].upper() + query_name[1:]
        generate_query(class_dir, query_name, data)
        print(query_name)
        count += 1

    print()
    print(f"{count} queries")


if __name__ == '__main__':
    main()
