from jobpilot.resume.template_map import map_editable_regions, source_metrics


def test_maps_only_bullet_regions_with_source_lines() -> None:
    source = r"""\documentclass{article}
\begin{document}
\section{Experience}
\begin{itemize}
\item Built \textbf{reliable} pipelines with 20\% fewer failures.
  Continued evidence on the next line.
\item Maintained local data quality checks.
\end{itemize}
\section{Education}
\begin{itemize}
\item Bachelor of Example Science.
\end{itemize}
\end{document}
"""
    regions = map_editable_regions(source, "a" * 64)
    assert [region.section for region in regions] == ["Experience", "Experience", "Education"]
    assert [region.line_start for region in regions] == [5, 7, 11]
    assert regions[0].line_end == 6
    assert "reliable" in regions[0].plain_text
    assert "20%" in regions[0].plain_text
    assert regions[0].region_id == "region-aaaaaaaaaaaa-001"


def test_metrics_report_external_dependencies_and_shell_escape_signal() -> None:
    source = r"""\documentclass[10pt]{article}
\input{resume-macros}
\includegraphics{portrait.png}
\immediate\write18{echo nope}
\section{Experience}
\begin{itemize}
\item Example.
\end{itemize}
"""
    regions = map_editable_regions(source, "b" * 64)
    metrics = source_metrics(source, regions)
    assert metrics["documentclass"] == "article"
    assert metrics["external_inputs"] == ["portrait.png", "resume-macros"]
    assert metrics["contains_write18"] is True
    assert metrics["bullet_count"] == 1
