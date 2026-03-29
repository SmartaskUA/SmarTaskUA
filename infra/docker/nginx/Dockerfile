FROM nginx:alpine

# Remove default nginx config to avoid conflicts
RUN rm /etc/nginx/conf.d/default.conf

# Copy custom nginx configuration
COPY infra/docker/nginx/nginx.conf /etc/nginx/nginx.conf

# Expose port 80
EXPOSE 80

# Start nginx
CMD ["nginx", "-g", "daemon off;"]
