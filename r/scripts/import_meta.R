# MANIFEST: {"name": "import_meta", "description": "Import monitoring site metadata for UK and European networks. Returns site codes, names, coordinates, and available pollutants as JSON.", "input_type": "import_params", "output_type": "series", "timeout": 60}
if (!requireNamespace("jsonlite", quietly = TRUE)) stop("jsonlite required")
if (!requireNamespace("openair", quietly = TRUE)) stop("openair required")

raw <- paste(readLines(file("stdin"), warn = FALSE), collapse = "")
payload <- jsonlite::fromJSON(raw, simplifyVector = FALSE)

network <- if (!is.null(payload$network)) payload$network else "aurn"

meta <- openair::importMeta(source = network)
if (is.null(meta) || nrow(meta) == 0) stop(paste0("No metadata for network='", network, "'"))

# Filter by site if provided
if (!is.null(payload$site)) {
  site_filter <- unlist(payload$site)
  meta <- meta[meta$code %in% site_filter | meta$site %in% site_filter, ]
}

cat(jsonlite::toJSON(meta, auto_unbox = TRUE, na = "null"))
