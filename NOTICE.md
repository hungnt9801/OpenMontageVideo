# NOTICE

## Origin

This repository is an independent fork of **OpenMontage**, created by
[Calesthio](https://github.com/calesthio) and published at
<https://github.com/calesthio/OpenMontage>.

It was imported from upstream commit
`08e2151fa02de28a5d6a312b3d575692bf147ad7` ("docs: add Objects in Overdrive
video showcase") **without** the upstream git history. No upstream commit
history, authorship metadata, or git remote is carried over.

All original code, documentation, agent skills, and assets remain the work of
the OpenMontage authors. This fork claims no authorship over them.

## License

OpenMontage is licensed under the **GNU Affero General Public License v3.0**
(AGPL-3.0). The full text is kept unchanged in [`LICENSE`](LICENSE).

This fork is distributed under the same license. Note AGPL-3.0 section 13: if
you run a modified version of this software to provide a service over a
network, you must offer the corresponding source to the users of that service.

Third-party components keep their own licenses — see
[`ink-theater/THIRD_PARTY_NOTICES.md`](ink-theater/THIRD_PARTY_NOTICES.md) and
the `LICENSE` / `LICENSE.txt` files bundled inside `.claude/skills/`.

## Local changes in this fork

Carried in with the initial import; see the import commit for the full diff.

- `lib/hyperframes_style_bridge.py` now reads the keys the playbook schema
  actually defines (`identity.name`, `identity.pace`,
  `color_palette.background`, `color_palette.muted`, `typography.headings`) and
  maps all five `identity.pace` enum values to distinct motion profiles.
- `scripts/backlot_simulate_run.py` records the `proposal` stage, so the
  simulator no longer trips the stage-prerequisite check.
- `tests/qa/conftest.py` stops pytest from executing the manual QA scripts
  while collecting `tests/`.
- `tests/tools/test_hyperframes_style_bridge_schema.py` added, and two fixtures
  that used the non-schema singular `heading` key updated.

## Upstream references

Some badges and promotional links in `README.md` still point at the original
project — its website (`openmontage.video`), YouTube channel (`@OpenMontage`),
X account, and the upstream sponsors table. They are kept as attribution to the
upstream project, not as claims of this fork.
