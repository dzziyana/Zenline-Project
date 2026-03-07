package com.zenline.model;

import java.util.Map;

public record TargetProduct(
    String reference,
    String name,
    String brand,
    String ean,
    String retailer,
    String url,
    Double price,
    String category,
    Map<String, Object> attributes
) {}
