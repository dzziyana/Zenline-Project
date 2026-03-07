package com.zenline.entity;

import io.quarkus.hibernate.orm.panache.PanacheEntity;
import jakarta.persistence.*;
import java.util.List;

@Entity
@Table(name = "product", indexes = {
    @Index(name = "idx_product_reference", columnList = "reference"),
    @Index(name = "idx_product_ean", columnList = "ean"),
    @Index(name = "idx_product_type", columnList = "productType"),
})
public class ProductEntity extends PanacheEntity {

    @Column(nullable = false)
    public String reference;

    @Column(nullable = false)
    public String name;

    public String brand;

    public String ean;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false)
    public ProductType productType;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "category_id")
    public CategoryEntity category;

    public Double price;

    /** Only for TARGET products */
    public String retailer;

    /** Only for TARGET products */
    public String url;

    @Column(columnDefinition = "TEXT")
    public String attributesJson;

    public static List<ProductEntity> findByCategory(CategoryEntity category, ProductType type) {
        return list("category = ?1 and productType = ?2", category, type);
    }

    public static ProductEntity findByReference(String reference) {
        return find("reference", reference).firstResult();
    }
}