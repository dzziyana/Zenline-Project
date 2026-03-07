package com.zenline.entity;

import io.quarkus.hibernate.orm.panache.PanacheEntity;
import jakarta.persistence.*;
import java.time.Instant;
import java.util.List;

@Entity
@Table(name = "match_run")
public class MatchRunEntity extends PanacheEntity {

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "category_id", nullable = false)
    public CategoryEntity category;

    public boolean useLlm;

    public double fuzzyThreshold;

    public int totalSources;

    public int totalMatches;

    @Column(nullable = false)
    public Instant createdAt;

    @OneToMany(mappedBy = "matchRun", cascade = CascadeType.ALL, orphanRemoval = true)
    public List<ProductMatchEntity> matches;

    @PrePersist
    void onCreate() {
        createdAt = Instant.now();
    }

    public static List<MatchRunEntity> findByCategory(CategoryEntity category) {
        return list("category", category);
    }

    public static MatchRunEntity findLatestByCategory(CategoryEntity category) {
        return find("category = ?1 order by createdAt desc", category).firstResult();
    }
}
