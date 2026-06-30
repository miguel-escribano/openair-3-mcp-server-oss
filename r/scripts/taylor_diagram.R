# MANIFEST: {"name": "taylor_diagram", "description": "Taylor diagram for model evaluation. Compare multiple model outputs against observations. series[0] = observations, rest = models.", "input_type": "series", "output_type": "image", "timeout": 60}
if (!requireNamespace("jsonlite", quietly = TRUE)) stop("jsonlite required")
if (!requireNamespace("openair", quietly = TRUE)) stop("openair required")
source(file.path(Sys.getenv("OPENAIR_R_LIB", unset = "r/common"), "series_df.R"))

raw <- paste(readLines(file("stdin"), warn = FALSE), collapse = "")
payload <- jsonlite::fromJSON(raw, simplifyVector = FALSE)

artifacts_dir <- Sys.getenv("OPENAIR_ARTIFACTS_DIR", unset = "artifacts")
dir.create(artifacts_dir, recursive = TRUE, showWarnings = FALSE)

timestamps <- unlist(payload$timestamps)
series_list <- payload$series
if (is.null(timestamps) || length(timestamps) == 0) stop("timestamps required")
if (length(series_list) < 2) stop("taylor_diagram requires obs (series[0]) and at least one model series")

df <- data.frame(date = as.POSIXct(timestamps, format = "%Y-%m-%dT%H:%M:%OSZ", tz = "UTC"), stringsAsFactors = FALSE)
cols <- character(length(series_list))
for (i in seq_along(series_list)) {
  s <- series_list[[i]]
  col <- openair_series_col_id(s$name, i)
  if (!nzchar(col)) col <- if (i == 1) "obs" else paste0("mod", i - 1)
  cols[i] <- col
  df[[col]] <- openair_mcp_values(s$values, length(timestamps))
}

obs_col <- cols[1]
mod_cols <- cols[-1]

outfile <- file.path(artifacts_dir, paste0("taylor_diagram_", format(Sys.time(), "%Y%m%d_%H%M%S"), ".png"))

grDevices::png(outfile, width = 900, height = 900, res = 120)
openair::TaylorDiagram(df, obs = obs_col, mod = mod_cols)
invisible(grDevices::dev.off())

cat(jsonlite::toJSON(list(
  artifact = normalizePath(outfile, winslash = "/", mustWork = FALSE),
  type = "png",
  summary = paste0("Taylor diagram: obs=", obs_col, ", models=", paste(mod_cols, collapse = ", ")),
  tool = "taylor_diagram"
), auto_unbox = TRUE))
