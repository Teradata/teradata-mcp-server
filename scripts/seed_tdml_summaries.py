"""
Seed script: connects to Teradata, extracts one-line summaries from teradataml
__init__.__doc__ for all TD_ANALYTIC_FUNCS, then prints the new dict[str, str]
block ready to paste into constants.py.

Requires DATABASE_URI env var:
  export DATABASE_URI="teradata://user:pass@host:1025/db"
  uv run python scripts/seed_tdml_summaries.py
"""

import os
import re
import textwrap
import warnings

warnings.filterwarnings("ignore")

import teradataml as tdml  # noqa: E402

# Connect so that teradataml populates __init__.__doc__ on each class
_uri = os.environ.get("DATABASE_URI", "")
if _uri:
    _m = re.match(r"teradata://([^:]+):([^@]+)@([^:]+):(\d+)/(.+)", _uri)
    if _m:
        tdml.create_context(
            host=_m.group(3),
            username=_m.group(1),
            password=_m.group(2),
            database=_m.group(5),
        )
    else:
        raise ValueError(f"Cannot parse DATABASE_URI: {_uri}")
else:
    raise EnvironmentError("DATABASE_URI not set — docstrings require a live connection")

FUNCS = [
    "ANOVA",
    "Attribution",
    "Antiselect",
    "Apriori",
    "BincodeFit",
    "BincodeTransform",
    "CFilter",
    "CategoricalSummary",
    "ChiSq",
    "ClassificationEvaluator",
    "ColumnSummary",
    "ColumnTransformer",
    "ConvertTo",
    "DecisionForest",
    "FTest",
    "FillRowId",
    "Fit",
    "GetFutileColumns",
    "GetRowsWithMissingValues",
    "GetRowsWithoutMissingValues",
    "GLM",
    "GLMPerSegment",
    "Histogram",
    "KMeans",
    "KMeansPredict",
    "KNN",
    "MovingAverage",
    "NERExtractor",
    "NGramSplitter",
    "NaiveBayesTextClassifierPredict",
    "NaiveBayesTextClassifierTrainer",
    "NonLinearCombineFit",
    "NonLinearCombineTransform",
    "NumApply",
    "NPath",
    "OneClassSVM",
    "OneClassSVMPredict",
    "OneHotEncodingFit",
    "OneHotEncodingTransform",
    "OrdinalEncodingFit",
    "OrdinalEncodingTransform",
    "OutlierFilterFit",
    "OutlierFilterTransform",
    "Pack",
    "PolynomialFeaturesFit",
    "PolynomialFeaturesTransform",
    "Pivoting",
    "QQNorm",
    "ROC",
    "RandomProjectionFit",
    "RandomProjectionMinComponents",
    "RandomProjectionTransform",
    "RegressionEvaluator",
    "RoundColumns",
    "RowNormalizeFit",
    "RowNormalizeTransform",
    "SMOTE",
    "SVM",
    "SVMPredict",
    "ScaleFit",
    "ScaleTransform",
    "Sessionize",
    "SentimentExtractor",
    "Shap",
    "Silhouette",
    "SimpleImputeFit",
    "SimpleImputeTransform",
    "StrApply",
    "StringSimilarity",
    "TDDecisionForestPredict",
    "TDGLMPredict",
    "TDNaiveBayesPredict",
    "TFIDF",
    "TargetEncodingFit",
    "TargetEncodingTransform",
    "TextMorph",
    "TextParser",
    "TrainTestSplit",
    "Transform",
    "UnivariateStatistics",
    "Unpack",
    "Unpivoting",
    "VectorDistance",
    "WhichMax",
    "WhichMin",
    "WordEmbeddings",
    "XGBoost",
    "XGBoostPredict",
    "ZTest",
]


def extract_summary(func_name: str) -> str:
    """Pull the first meaningful sentence from the teradataml __init__ docstring."""
    func_obj = getattr(tdml, func_name, None)
    if func_obj is None:
        return f"Teradata ML analytic function {func_name}."

    raw = getattr(func_obj.__init__, "__doc__", None) or ""
    # Dedent and strip leading blank lines
    raw = textwrap.dedent(raw).strip()

    # The teradataml pattern is:
    #   DESCRIPTION:
    #       <summary text, may span multiple lines>
    #
    #   PARAMETERS:
    # Try to grab the DESCRIPTION block first.
    desc_match = re.search(r"DESCRIPTION\s*:\s*\n(.*?)(?:\n\s*\n|\n\s*PARAMETERS\s*:)", raw, re.DOTALL)
    if desc_match:
        block = desc_match.group(1)
    else:
        # Fallback: take the first non-empty paragraph
        block = raw.split("\n\n")[0]

    # Collapse internal whitespace / newlines into a single line
    block = re.sub(r"\s+", " ", block).strip()

    # Replace teradataml-specific terminology
    block = block.replace("teradataml DataFrame", "table name")
    block = block.replace("DataFrame", "table name")

    # Truncate at the first sentence boundary (period followed by space or end)
    # Keep the trailing period.
    sent_match = re.search(r"^(.*?\.)\s", block)
    if sent_match:
        summary = sent_match.group(1)
    else:
        # No sentence boundary — use the whole block but cap length
        summary = block[:200].rstrip()
        if not summary.endswith("."):
            summary += "."

    return summary


def main():
    results: list[tuple[str, str]] = []
    missing: list[str] = []

    for name in FUNCS:
        summary = extract_summary(name)
        results.append((name, summary))
        if "analytic function" in summary and name in summary:
            missing.append(name)

    # Print the dict literal ready to paste into constants.py
    print("TD_ANALYTIC_FUNCS = {")
    for name, summary in results:
        # Escape any quotes inside the summary
        safe = summary.replace('"', '\\"')
        print(f'    "{name}": "{safe}",')
    print("}")

    if missing:
        print(f"\n# WARNING: {len(missing)} functions had no extractable docstring — fallback used:")
        for m in missing:
            print(f"#   {m}")


if __name__ == "__main__":
    main()
