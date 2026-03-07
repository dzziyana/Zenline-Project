package com.zenline.service;

import com.zenline.client.MatcherClient;
import com.zenline.model.MatchRequest;
import com.zenline.model.MatchResult;
import jakarta.enterprise.context.ApplicationScoped;
import jakarta.inject.Inject;
import org.eclipse.microprofile.rest.client.inject.RestClient;

import java.util.Map;

@ApplicationScoped
public class ProductService {

    @Inject
    @RestClient
    MatcherClient matcherClient;

    public Map<String, Object> getCategories() {
        return matcherClient.getCategories();
    }

    public Map<String, Object> getSourceProducts(String category) {
        return matcherClient.getSourceProducts(category);
    }

    public Map<String, Object> getTargetProducts(String category) {
        return matcherClient.getTargetProducts(category);
    }

    public MatchResult runMatching(String category, boolean useLlm, double fuzzyThreshold) {
        return matcherClient.runMatching(new MatchRequest(category, useLlm, fuzzyThreshold));
    }
}
