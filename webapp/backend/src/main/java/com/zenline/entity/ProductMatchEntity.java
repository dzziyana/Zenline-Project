package com.zenline.entity;

import io.quarkus.hibernate.orm.panache.PanacheEntity;
import jakarta.persistence.*;

@Entity
@Table(name = "product_match", indexes = {
    @Index(name = "idx_match_run", columnList = "match_run_id"),
    @Index(name = "idx_match_source", columnList = "source_product_id"),
})
public class ProductMatchEntity extends PanacheEntity {

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "match_run_id", nullable = false)
    public MatchRunEntity matchRun;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "source_product_id", nullable = false)
    public ProductEntity sourceProduct;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "target_product_id", nullable = false)
    public ProductEntity targetProduct;

    public double confidence;

    @Column(nullable = false)
    public String matchMethod;

    public String competitorRetailer;

    public String competitorProductName;

    public String competitorUrl;

    public Double competitorPrice;
}
