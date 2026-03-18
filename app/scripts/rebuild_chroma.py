from app.services.retrieval_service import RetrievalService


if __name__ == "__main__":
    service = RetrievalService()
    print(service.rebuild_index(force=True))
