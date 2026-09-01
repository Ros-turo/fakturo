import pytest
from schemas import ClientDefault
from pydantic import ValidationError


@pytest.mark.parametrize("ico", ["12", '1234567890', "1234567t", " " ], ids= ["prilis kratke", "prilis dlouhe", "obsahuje pismeno", "prazdnej string"])
def test_ico(ico):
    with pytest.raises(ValidationError):
        ClientDefault(
            name="Ros",
            ico=ico,
            city="Prague",
            psc="qwjfi"
        )