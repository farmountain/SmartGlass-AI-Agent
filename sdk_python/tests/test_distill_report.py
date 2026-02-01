from sdk_python.distill.report import DistillationReport, summarize_report
from sdk_python.skill_template.trainer import FitResult, SkillTrainerConfig


def test_distillation_report_records_runs(tmp_path):
    config = SkillTrainerConfig(dataset="demo", epochs=3, lam_align=0.5)
    fit = FitResult(final_loss=0.25, residual_std=0.1, loss_history=[0.5, 0.3, 0.25])

    path = tmp_path / "report.json"
    reporter = DistillationReport(path)
    reporter.record_run(skill="demo", step=1, config=config, fit_result=fit, extra_metadata={"qlora": True})

    payload = reporter.to_dict()
    assert payload["skills"]["demo"]["runs"][0]["fit_result"]["loss_history"] == [0.5, 0.3, 0.25]

    summary = summarize_report(path)
    assert summary["skills"]["demo"]["runs"] == 1
    assert summary["skills"]["demo"]["best_final_loss"] == 0.25
