# MANIFEST: {"name": "import_meta", "description": "Import monitoring site metadata for UK and European networks. Supports openair 3.2 importMeta filters (code, site, site_type, pollutant, lat/lng, max_dist, max_n, year, all).", "input_type": "import_params", "output_type": "series", "timeout": 60}
if (!requireNamespace("jsonlite", quietly = TRUE)) stop("jsonlite required")
if (!requireNamespace("openair", quietly = TRUE)) stop("openair required")

raw <- paste(readLines(file("stdin"), warn = FALSE), collapse = "")
payload <- jsonlite::fromJSON(raw, simplifyVector = FALSE)

network <- if (!is.null(payload$network)) payload$network else "aurn"

meta_args <- list(source = network)

if (!is.null(payload$year)) meta_args$year <- payload$year
poll <- payload$meta_pollutant
if (!is.null(poll) && length(poll) > 0) meta_args$pollutant <- unlist(poll)
if (!is.null(payload$code) && length(payload$code) > 0) meta_args$code <- unlist(payload$code)
if (!is.null(payload$site) && length(payload$site) > 0) {
  sites <- unlist(payload$site)
  if (is.null(meta_args$code)) {
    looks_code <- function(x) {
      x <- as.character(x)[1]
      grepl("^[A-Za-z]{1,4}[0-9]?$", x)
    }
    if (length(sites) == 1L && isTRUE(looks_code(sites[1]))) {
      meta_args$code <- sites
    } else {
      meta_args$site <- sites
    }
  }
}
if (!is.null(payload$site_type) && length(payload$site_type) > 0) {
  meta_args$site_type <- unlist(payload$site_type)
}
if (!is.null(payload$lat)) meta_args$lat <- as.numeric(payload$lat)
if (!is.null(payload$lng)) meta_args$lng <- as.numeric(payload$lng)
if (!is.null(payload$max_dist)) meta_args$max_dist <- as.numeric(payload$max_dist)
if (!is.null(payload$max_n)) meta_args$max_n <- as.integer(payload$max_n)
all_flag <- payload$all_meta
if (is.null(all_flag) && !is.null(payload$all)) all_flag <- payload$all
if (isTRUE(all_flag)) meta_args$all <- TRUE
if (isTRUE(payload$duplicate)) meta_args$duplicate <- TRUE

meta <- do.call(openair::importMeta, meta_args)
if (is.null(meta) || nrow(meta) == 0) {
  stop(paste0("No metadata for network='", network, "' with the given filters"))
}

# Always return a JSON object ({"sites": [...]}), never a bare array — a bare
# top-level array fails FastMCP's structured-content validation
# ("structured_content must be a dict or None. Got list: ...").
cat(jsonlite::toJSON(list(sites = meta), auto_unbox = TRUE, na = "null"))