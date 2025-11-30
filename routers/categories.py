import sqlite3

from fastapi import APIRouter, HTTPException, Response
from starlette import status

from models import CategorySchema

try:  # pragma: no cover - dependency may be absent in test environment
    from asyncpg.exceptions import UniqueViolationError, ForeignKeyViolationError
except ModuleNotFoundError:  # pragma: no cover
    class UniqueViolationError(Exception):
        ...

    class ForeignKeyViolationError(Exception):
        ...

from controllers import read_categories, write_category, read_category, purge_category, check_category_has_products

router = APIRouter()


@router.get('/', response_model=list[CategorySchema])
async def get_categories():
    return await read_categories()


@router.post('/', response_model=CategorySchema)
async def add_category(name: str):
    try:
        return await write_category(name=name)
    except (UniqueViolationError, sqlite3.IntegrityError) as e:
        # Проверяем, что это действительно ошибка уникальности
        error_str = str(e).lower()
        if 'unique' in error_str or 'constraint' in error_str:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Category already exists')
        raise


@router.delete('/', response_model=CategorySchema)
async def delete_category(name: str):
    check_category = await read_category(name=name)
    if check_category:
        # Проверяем, есть ли продукты в категории
        has_products = await check_category_has_products(check_category['id'])
        if has_products:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail='There are still products in the category')
        
        try:
            await purge_category(name=name)
            return Response(status_code=status.HTTP_200_OK)
        except Exception as e:
            # Если все-таки произошла ошибка (например, foreign key constraint)
            error_str = str(e).lower()
            if 'foreign' in error_str or 'constraint' in error_str:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                    detail='There are still products in the category')
            raise
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Category does not exist')