package com.zenline.resource;

import com.zenline.model.MatchResult;
import com.zenline.service.ProductService;
import jakarta.inject.Inject;
import jakarta.ws.rs.*;
import jakarta.ws.rs.core.MediaType;

import java.util.Map;

@Path("/api")
@Produces(MediaType.APPLICATION_JSON)
public class ProductResource {

    @Inject
    ProductService productService;

    @GET
    @Path("/categories")
    public Map<String, Object> getCategories() {
        return productService.getCategories();
    }

    @GET
    @Path("/products/source/{category}")
    public Map<String, Object> getSourceProducts(@PathParam("category") String category) {
        return productService.getSourceProducts(category);
    }

    @GET
    @Path("/products/target/{category}")
    public Map<String, Object> getTargetProducts(@PathParam("category") String category) {
        return productService.getTargetProducts(category);
    }

    @POST
    @Path("/match/{category}")
    @Consumes(MediaType.APPLICATION_JSON)
    public MatchResult runMatching(
            @PathParam("category") String category,
            @QueryParam("useLlm") @DefaultValue("false") boolean useLlm,
            @QueryParam("fuzzyThreshold") @DefaultValue("75.0") double fuzzyThreshold
    ) {
        return productService.runMatching(category, useLlm, fuzzyThreshold);
    }
}
