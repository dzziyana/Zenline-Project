package com.zenline.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import java.util.List;

public record SourceProductSubmission(
    @JsonProperty("source_reference") String sourceReference,
    List<CompetitorMatch> competitors
) {}