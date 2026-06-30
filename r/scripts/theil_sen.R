# MANIFEST: {"name": "theil_sen", "description": "Non-parametric trend analysis using Theil-Sen estimator. Shows trend magnitude and significance.", "input_type": "series", "output_type": "image", "timeout": 120}
if (!requireNamespace("jsonlite", quietly = TRUE)) stop("jsonlite required")
if (!requireNamespace("openair", quietly = TRUE)) stop("openair required")
source(file.path(Sys.getenv("OPENAIR_R_LIB", unset = "r/common"), "series_df.R"))

raw <- paste(readLines(file("stdin"), warn = FALSE), collapse = "")
payload <- jsonlite::fromJSON(raw, simplifyVector = FALSE)

artifacts_dir <- Sys.getenv("OPENAIR_ARTIFACTS_DIR", unset = "artifacts")
dir.create(artifacts_dir, recursive = TRUE, showWarnings = FALSE)

built <- openair_build_series_df(payload)
df <- built$df
pollutants <- built$pollutants
payload <- built$payload
summary_labs <- openair_summary_labels(payload)

outfile <- file.path(artifacts_dir, paste0("theil_sen_", format(Sys.time(), "%Y%m%d_%H%M%S"), ".png"))

grDevices::png(outfile, width = 1200, height = 600, res = 120)
openair::TheilSen(df, pollutant = pollutants[1], main = openair_plot_title(payload))
invisible(grDevices::dev.off())

cat(jsonlite::toJSON(list(
  artifact = normalizePath(outfile, winslash = "/", mustWork = FALSE),
  type = "png",
  summary = paste0("Theil-Sen trend analysis for ", summary_labs[1]),
  tool = "theil_sen"
), auto_unbox = TRUE))
