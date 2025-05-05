def get_param_from_request(request, view, param_name='id'):
    return (
            view.kwargs.get('pk') or  # Из URL параметров
            request.query_params.get(param_name) or  # Из query параметров н-р(?user_id=)
            request.data.get(param_name)  # Из тела запроса
    )
