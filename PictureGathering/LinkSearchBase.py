# coding: utf-8
import configparser
import logging.config
import os
import re

from abc import ABCMeta, abstractmethod
from logging import INFO, getLogger
from pathlib import Path


logging.config.fileConfig("./log/logging.ini", disable_existing_loggers=False)
logger = getLogger("root")
logger.setLevel(INFO)


class LinkSearchBase():
    """外部リンク探索処理を担うクラスの基底クラス

    Notes:
        CoR = Chain of Responsibilityパターン
        この基底クラスのインスタンスを作成し、
        派生クラスにて機能を実装した担当者をRegisterで登録する。
        CoRProcessCheck/CoRProcessDoにて登録した担当者に仕事を発注する。
        派生クラスはIsTargetUrlとProcessをオーバーライドして実装する必要がある。

    Attributes:
        processer_list (LinkSearchBase[]): 処理担当者リスト
    """
    def __init__(self):
        self.processer_list = []

    def Register(self, processer) -> int:
        """担当者登録

        Args:
            processer (LinkSearchBase): 担当者

        Returns:
            int: 成功時0, 失敗時-1
        """
        interface_check = hasattr(processer, "IsTargetUrl") and hasattr(processer, "Process")
        if not interface_check:
            return -1
        self.processer_list.append(processer)
        return 0

    def CoRProcessDo(self, url: str) -> int:
        """処理実行メイン

        Notes:
            大元のLinkSearchBaseからのみ呼ばれる想定。
            self.processer_listに担当者が登録されていないと処理されない。

        Args:
            url (str): 処理対象url

        Returns:
            int: いずれかの担当者が処理を実行して成功した時0
                 担当者は見つかったが処理が失敗した時-1
                 担当者が見つからなかった時1
        """
        cor_result = 1  # 担当者発見フラグ
        proc_result = -1  # 処理成功フラグ

        # CoR
        for p in self.processer_list:
            if p.IsTargetUrl(url):
                cor_result = 0
                proc_result = p.Process(url)
                break  # 初めに見つかった担当者でのみ処理する
        
        # 返り値の意味はReturns参照
        return 1 if (cor_result == 1) else proc_result

    def CoRProcessCheck(self, url: str) -> bool:
        """処理実行確認

        Notes:
            大元のLinkSearchBaseからのみ呼ばれる想定。
            self.processer_listに登録されている、
            担当者のいずれかが処理できるかどうかを返す。
            実際に処理は行わない。

        Args:
            url (str): 処理対象url

        Returns:
            bool: 処理できるいずれかの担当者が見つかった時True
                  処理できる担当者が見つからなかった時False
        """
        cor_result = 1  # 担当者発見フラグ

        # CoR
        for p in self.processer_list:
            if p.IsTargetUrl(url):
                cor_result = 0
                break
        
        # 返り値の意味はReturns参照
        return (cor_result == 0)

    def IsTargetUrl(self, url: str) -> bool:
        """自分（担当者）が処理できるurlかどうか返す関数

        Notes:
            派生クラスでオーバーライドする。
            基底クラスでは常にFalseを返す。

        Args:
            url (str): 処理対象url

        Returns:
            bool: 担当urlだった場合True, そうでない場合False
        """
        return False

    def Process(self, url: str) -> int:
        """自分（担当者）が担当する処理

        Notes:
            派生クラスでオーバーライドする。
            基底クラスでは常に何もせず、失敗扱いとする。

        Args:
            url (str): 処理対象url
            save_base (str): 保存先ベースパス

        Returns:
            int: 成功時0, 失敗時-1
        """
        return -1


class LSConcrete_0(LinkSearchBase):
    def __init__(self):
        super().__init__()

    def IsTargetUrl(self, url: str) -> bool:
        pattern = r"^https://www.anyurl/sample/index_0.html$"
        regex = re.compile(pattern)
        is_target = not (regex.findall(url) == [])
        if is_target:
            logger.info("LSConcrete_0.IsTargetUrl catch")
        return is_target

    def Process(self, url: str) -> int:
        logger.info("LSConcrete_0.Process called")
        return 0


class LSConcrete_1(LinkSearchBase):
    def __init__(self):
        super().__init__()

    def IsTargetUrl(self, url: str) -> bool:
        pattern = r"^https://www.anyurl/sample/index_1.html$"
        regex = re.compile(pattern)
        is_target = not (regex.findall(url) == [])
        if is_target:
            logger.info("LSConcrete_1.IsTargetUrl catch")
        return is_target

    def Process(self, url: str) -> int:
        logger.info("LSConcrete_1.Process called")
        return 0


class LSConcrete_2(LinkSearchBase):
    def __init__(self):
        super().__init__()

    def IsTargetUrl(self, url: str) -> bool:
        pattern = r"^https://www.anyurl/sample/index_2.html$"
        regex = re.compile(pattern)
        is_target = not (regex.findall(url) == [])
        if is_target:
            logger.info("LSConcrete_2.IsTargetUrl catch")
        return is_target

    def Process(self, url: str) -> int:
        logger.info("LSConcrete_2.Process called")
        return -1  # 常に処理失敗するものとする


if __name__ == "__main__":
    ls_base = LinkSearchBase()
    # url = "https://www.pixiv.net/artworks/86704541"
    # url = "http://nijie.info/view_popup.php?id=409587"
    url = "https://www.anyurl/sample/index_{}.html"

    # 具体的な担当者を登録
    lsc = LSConcrete_0()
    ls_base.Register(lsc)
    lsc = LSConcrete_1()
    ls_base.Register(lsc)
    lsc = LSConcrete_2()
    ls_base.Register(lsc)

    # CoR実行
    for i in range(0, 4):
        res = ls_base.CoRProcessCheck(url.format(i))
        if not res:
            logger.info("any LSConcrete cannot catch")

    for i in range(0, 4):
        res = ls_base.CoRProcessDo(url.format(i))
        if res == 1:
            logger.info("any LSConcrete cannot Process")
        elif res == -1:
            logger.info("LSConcrete Process called but failed")

    pass
