package com.zenline.model;

import com.fasterxml.jackson.annotation.JsonProperty;

public record MatchRequest(
    String category,
    @JsonProperty("use_llm") boolean useLlm,
    @JsonProperty("fuzzy_threshold") double fuzzyThreshold
) {
    public MatchRequest(String category) {
        this(category, false, 75.0);
    }
}
