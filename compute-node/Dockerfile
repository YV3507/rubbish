FROM rust:1.77-slim AS builder

WORKDIR /app
COPY Cargo.toml Cargo.lock* ./
COPY src/ ./src/
RUN cargo build --release

FROM debian:bookworm-slim
WORKDIR /app
COPY --from=builder /app/target/release/rubbish-compute /app/compute-node
RUN mkdir -p /data
ENV COMPUTE_DB_PATH=/data/codegraph.db
EXPOSE 8080
CMD ["/app/compute-node"]
