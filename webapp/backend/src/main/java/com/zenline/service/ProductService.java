package com.zenline.service;

import com.zenline.client.MatcherClient;
import com.zenline.model.MatchRequest;
import com.zenline.model.MatchResult;
import jakarta.enterprise.context.ApplicationScoped;
import jakarta.inject.Inject;
import org.eclipse.microprofile.rest.client.inject.RestClient;
import org.jboss.logging.Logger;

import java.util.List;
import java.util.Map;

@ApplicationScoped
public class ProductService {

    private static final Logger LOG = Logger.getLogger(ProductService.class);

    @Inject
    @RestClient
    MatcherClient matcherClient;

    public Map<String, Object> getCategories() {
        try {
            return matcherClient.getCategories();
        } catch (Exception e) {
            LOG.warn("Matcher service unavailable at localhost:8081 — returning empty categories");
            return Map.of("categories", List.of());
        }
    }

    public Map<String, Object> getSourceProducts(String category) {
        try {
            return matcherClient.getSourceProducts(category);
        } catch (Exception e) {
            LOG.warn("Matcher service unavailable — returning empty source products");
            return Map.of("products", List.of());
        }
    }

    public Map<String, Object> getTargetProducts(String category) {
        try {
            return matcherClient.getTargetProducts(category);
        } catch (Exception e) {
            LOG.warn("Matcher service unavailable — returning empty target products");
            return Map.of("products", List.of());
        }
    }

    public MatchResult runMatching(String category, boolean useLlm, double fuzzyThreshold) {
        return matcherClient.runMatching(new MatchRequest(category, useLlm, fuzzyThreshold));
    }
}
