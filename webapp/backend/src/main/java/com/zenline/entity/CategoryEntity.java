package com.zenline.entity;

import io.quarkus.hibernate.orm.panache.PanacheEntity;
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Table;

@Entity
@Table(name = "category")
public class CategoryEntity extends PanacheEntity {

    @Column(nullable = false, unique = true)
    public String name;

    public static CategoryEntity findByName(String name) {
        return find("name", name).firstResult();
    }

    public static CategoryEntity findOrCreate(String name) {
        CategoryEntity existing = findByName(name);
        if (existing != null) return existing;
        CategoryEntity entity = new CategoryEntity();
        entity.name = name;
        entity.persist();
        return entity;
    }
}