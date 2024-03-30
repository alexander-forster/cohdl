from __future__ import annotations


class MakeTarget:
    def __init__(
        self,
        target_str,
        commands: list[str] | str,
        dep: list[MakeTarget | str] = [],
        required_by: list[MakeTarget | str] = [],
        *,
        order_only: list[MakeTarget | str] = [],
        phony=False,
        lock=False,
    ):
        assert not (phony and lock), "lock cannot be set for phony target"

        if isinstance(commands, str):
            commands = [commands]

        self.target_str = target_str
        self.commands = commands
        self.dep: dict[str, str | MakeTarget] = {}
        self.order_only: dict[str, str | MakeTarget] = {}

        self.add_dependency(*dep)
        self.add_dependency(*order_only, order_only=True)

        self.required_by: list[str] = [
            x if isinstance(x, str) else x.target_str for x in required_by
        ]

        self.phony = phony
        self.lock = lock

    def add_dependency(self, *dep: str | MakeTarget, order_only=False):
        if order_only:
            result_dict = self.order_only
        else:
            result_dict = self.dep

        for d in dep:
            d_str = d if isinstance(d, str) else d.target_str
            result_dict[d_str] = d

    def __hash__(self) -> int:
        return id(self)

    def collect_all_targets(self) -> dict[str, MakeTarget]:
        result: dict[str, MakeTarget] = {self.target_str: self}

        for dep in self.dep.values():
            if isinstance(dep, MakeTarget):
                result = {**result, **dep.collect_all_targets()}

        for dep in self.order_only.values():
            if isinstance(dep, MakeTarget):
                result = {**result, **dep.collect_all_targets()}

        return result

    def generate_makefile(*targets: MakeTarget, path: str, lock_dir: str | None = None):
        all_targets: dict[str, MakeTarget] = {}

        if lock_dir is not None:
            lock_dir_target = MakeTarget(lock_dir, f"mkdir {lock_dir}")
        else:
            lock_dir_target = None

        for target in targets:
            all_targets = {**all_targets, **target.collect_all_targets()}

        for prerequisit in all_targets.values():
            for r in prerequisit.required_by:
                all_targets[r].add_dependency(prerequisit)

        with open(path, "w+") as file:
            phony = [
                target.target_str for target in all_targets.values() if target.phony
            ]

            lock_targets = [
                target.target_str for target in all_targets.values() if target.lock
            ]

            if len(phony) != 0:
                file.writelines([f".PHONY: {' '.join(phony)}\n", "\n"])

            def write_target(target: MakeTarget):
                cmds = [*target.commands]

                if target.lock:
                    assert (
                        lock_dir_target is not None
                    ), "target.lock is set but no lock_dir was specified"
                    target_str = f"{lock_dir}/{target.target_str}"
                    target.add_dependency(lock_dir_target, order_only=True)
                    cmds.append(f"touch {target_str}")
                else:
                    target_str = target.target_str

                def format_dep(dep: str):
                    if dep in lock_targets:
                        return f"{lock_dir}/{dep}"
                    return dep

                normal_dep = " ".join([format_dep(dep) for dep in target.dep.keys()])
                order_only = [format_dep(dep) for dep in target.order_only.keys()]

                if len(order_only) == 0:
                    order_only_dep = ""
                else:
                    order_only_dep = " | " + " ".join(order_only)

                file.writelines(
                    [
                        f"{target_str}: {normal_dep}{order_only_dep}\n",
                        *[f"\t{cmd}\n" for cmd in cmds],
                        "\n",
                    ]
                )

            # write targets received as arguments in order (ensure, that first target appears first in Makefile)
            for target in targets:
                write_target(target)
                del all_targets[target.target_str]

            # write remaining targets
            for target in all_targets.values():
                write_target(target)

            if lock_dir_target is not None:
                write_target(lock_dir_target)
