package com.zenline.model;

import java.util.Map;

public record SourceProduct(
    String reference,
    String name,
    String brand,
    String ean,
    String category,
    Double price,
    Map<String, Object> attributes
) {}
