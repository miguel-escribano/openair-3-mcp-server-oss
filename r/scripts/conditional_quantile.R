# MANIFEST: {"name": "conditional_quantile", "description": "Conditional quantile plot for model evaluation. Compare predicted (series[0]) vs observed (series[1]) values.", "input_type": "series", "output_type": "image", "timeout": 90}
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
if (length(series_list) < 2) stop("conditional_quantile requires obs (series[0]) and mod (series[1])")

s_obs <- series_list[[1]]
s_mod <- series_list[[2]]
obs_col <- openair_series_col_id(s_obs$name, 1)
if (!nzchar(obs_col)) obs_col <- "obs"
mod_col <- openair_series_col_id(s_mod$name, 2)
if (!nzchar(mod_col)) mod_col <- "mod"

df <- data.frame(
  date = as.POSIXct(timestamps, format = "%Y-%m-%dT%H:%M:%OSZ", tz = "UTC"),
  stringsAsFactors = FALSE
)
df[[obs_col]] <- openair_mcp_values(s_obs$values, length(timestamps))
df[[mod_col]] <- openair_mcp_values(s_mod$values, length(timestamps))

outfile <- file.path(artifacts_dir, paste0("conditional_quantile_", format(Sys.time(), "%Y%m%d_%H%M%S"), ".png"))

grDevices::png(outfile, width = 900, height = 900, res = 120)
openair::conditionalQuantile(df, obs = obs_col, mod = mod_col)
invisible(grDevices::dev.off())

cat(jsonlite::toJSON(list(
  artifact = normalizePath(outfile, winslash = "/", mustWork = FALSE),
  type = "png",
  summary = paste0("Conditional quantile: obs=", obs_col, " vs mod=", mod_col),
  tool = "conditional_quantile"
), auto_unbox = TRUE))
