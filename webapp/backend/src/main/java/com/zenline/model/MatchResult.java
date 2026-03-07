package com.zenline.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import java.util.List;

public record MatchResult(
    String category,
    @JsonProperty("total_sources") int totalSources,
    @JsonProperty("total_matches") int totalMatches,
    List<SourceProductSubmission> submissions
) {}