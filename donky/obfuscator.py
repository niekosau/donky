import multiprocessing
import socket
import sqlalchemy
import time
import logging


class Obfuscator():

    db_engine = sqlalchemy.create_engine(
            url="mysql+pymysql://localhost/mysql",
            pool_size=10)
    _logger = logging.getLogger("Donky")

    def __init__(self, proc: int = 4, port: int = 3306, socket_timeout: int = 10):
        self.__wait_for_port(port=port, timeout=socket_timeout)
        self.num_proc = self._check_cpu_count(proc=proc)
        self.execute_query("SET GLOBAL innodb_flush_log_at_trx_commit=2,sync_binlog=0")  # Some speed optimization for mysql

    def __del__(self) -> None:
        """
        Dispose sqlalchemy engine when all class reference are removed
        """
        self.db_engine.dispose()

    def __initializer(self) -> None:
        """
        Initializer for sqlalchemy engine with multiprocessing support
        """
        self.db_engine.dispose(close=False)

    def __init_proc_pool(self) -> multiprocessing.Pool:
        """
        Create process pool
        """
        with multiprocessing.Pool(processes=self.num_proc, initializer=self.__initializer) as proc_pool:
            return proc_pool

    def __wait_for_port(self, port: int, timeout: int) -> bool:
        self._logger.info(f"Waiting for {port} to be opened")
        _socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        _socket.settimeout(timeout)
        for i in range(timeout):
            self._logger.debug(f"Waiting for port: {port}")
            time.sleep(1)
            if _socket.connect_ex(("127.0.0.1", port)) == 0:
                return
        raise TimeoutError(f"Timeout waiting for {port}")

    def _check_cpu_count(self, proc: int) -> int:
        """
        Check if requested process count less or equal to
        number of system cores.
        """
        core_count = multiprocessing.cpu_count()
        self._logger.debug(f"CPU core count: {core_count}")
        return proc if proc <= core_count else core_count

    def remove_comments(self, query: str) -> str:
        """
        Removing comments from line
        """
        id = query.find("--")
        if id > 0:
            query = query[:id]
        return query

    def remove_empty_line(self, queries: list) -> list:
        """
        Remove empty elements from list
        """
        return [q for q in queries if q]

    def assemble_full_queries(self, queries: list) -> list:
        """
        reassemble list and split by comma
        """
        return " ".join(queries).split(";")[:-1]

    def load_sql_file(self, sql_file: str) -> list:
        """
        Load sql queries from text file
        """
        with open(sql_file, "r") as file:
            queries = [line.strip() for line in file.readlines()]
        queries = [self.remove_comments(q) for q in queries]
        queries = self.remove_empty_line(queries)
        queries = self.assemble_full_queries(queries)
        self._logger.debug(f"SQL query count: {len(queries)}")
        return queries

    def execute_query(self, query: str) -> None:
        """
        Execute sql query
        """
        with self.db_engine.connect() as conn:
            self._logger.debug(f"Executing: {query}")
            conn.execute(sqlalchemy.text(query))

    def obfuscate(self) -> None:
        """
        Execute obfuscator
        """
        self._logger.info("DB obfustator is starting")
        obf_queries = self.load_sql_file(sql_file="etc/donky/test.sql")
        with multiprocessing.Pool(processes=self.num_proc, initializer=self.__initializer) as proc_pool:
            proc_pool.map(self.execute_query, obf_queries)
        self._logger.info("DB obfuscator finished")
