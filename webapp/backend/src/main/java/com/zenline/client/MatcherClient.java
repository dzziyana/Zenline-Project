package com.zenline.client;

import com.zenline.model.MatchRequest;
import com.zenline.model.MatchResult;
import jakarta.ws.rs.*;
import jakarta.ws.rs.core.MediaType;
import org.eclipse.microprofile.rest.client.inject.RegisterRestClient;
import java.util.Map;

@Path("/")
@RegisterRestClient
public interface MatcherClient {

    @GET
    @Path("/health")
    @Produces(MediaType.APPLICATION_JSON)
    Map<String, String> health();

    @GET
    @Path("/categories")
    @Produces(MediaType.APPLICATION_JSON)
    Map<String, Object> getCategories();

    @GET
    @Path("/products/source/{category}")
    @Produces(MediaType.APPLICATION_JSON)
    Map<String, Object> getSourceProducts(@PathParam("category") String category);

    @GET
    @Path("/products/target/{category}")
    @Produces(MediaType.APPLICATION_JSON)
    Map<String, Object> getTargetProducts(@PathParam("category") String category);

    @POST
    @Path("/match")
    @Consumes(MediaType.APPLICATION_JSON)
    @Produces(MediaType.APPLICATION_JSON)
    MatchResult runMatching(MatchRequest request);
}
