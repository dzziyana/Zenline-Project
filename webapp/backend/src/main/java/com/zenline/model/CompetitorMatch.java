transpackage com.zenline.model;

import com.fasterxml.jackson.annotation.JsonProperty;

public record CompetitorMatch(
    String reference,
    @JsonProperty("competitor_retailer") String competitorRetailer,
    @JsonProperty("competitor_product_name") String competitorProductName,
    @JsonProperty("competitor_url") String competitorUrl,
    @JsonProperty("competitor_price") Double competitorPrice,
    Double confidence,
    @JsonProperty("match_method") String matchMethod
) {}
